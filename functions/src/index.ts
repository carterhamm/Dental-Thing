import { onRequest } from 'firebase-functions/v2/https';
import { onDocumentCreated } from 'firebase-functions/v2/firestore';
import { defineSecret } from 'firebase-functions/params';
import { initializeApp } from 'firebase-admin/app';
import { getFirestore, FieldValue } from 'firebase-admin/firestore';

initializeApp();
const db = getFirestore();

const elevenLabsKey = defineSecret('ELEVENLABS_API_KEY');
const elevenLabsVoice = defineSecret('ELEVENLABS_VOICE_ID');

// --- Helper ---

async function logActivity(icon: string, message: string, type: string) {
  await db.collection('activity_log').add({
    icon,
    message,
    type,
    timestamp: FieldValue.serverTimestamp(),
  });
}

// --- When a cancellation is created, start outreach ---

export const onCancellation = onDocumentCreated(
  'cancellations/{id}',
  async (event) => {
    const data = event.data?.data();
    if (!data) return;

    await logActivity('⚠️', `Cancellation received — ${data.patientName}`, 'warning');

    // Get queued patients
    const patientsSnap = await db.collection('patients')
      .where('status', '==', 'queued')
      .orderBy('order')
      .get();

    if (patientsSnap.empty) {
      await logActivity('❌', 'No patients available for outreach', 'warning');
      return;
    }

    // Start calling the first patient
    const first = patientsSnap.docs[0];
    await first.ref.update({ status: 'calling' });

    await db.doc('agent/status').set({
      phase: 'calling',
      currentPatient: first.data().name,
      attempt: 1,
      totalPatients: patientsSnap.size,
    });

    await db.doc('slots/active').update({ status: 'open' });
    await logActivity('📞', `Calling ${first.data().name}...`, 'call');
  }
);

// --- Generate TTS via ElevenLabs ---

export const generateSpeech = onRequest(
  {
    cors: true,
    secrets: [elevenLabsKey, elevenLabsVoice],
  },
  async (req, res) => {
    const { text } = req.body;
    if (!text) {
      res.status(400).json({ error: 'text is required' });
      return;
    }

    const response = await fetch(
      `https://api.elevenlabs.io/v1/text-to-speech/${elevenLabsVoice.value()}`,
      {
        method: 'POST',
        headers: {
          'xi-api-key': elevenLabsKey.value(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text,
          model_id: 'eleven_turbo_v2_5',
          voice_settings: {
            stability: 0.5,
            similarity_boost: 0.75,
            style: 0.3,
          },
        }),
      }
    );

    if (!response.ok) {
      res.status(500).json({ error: 'ElevenLabs TTS failed' });
      return;
    }

    const buffer = Buffer.from(await response.arrayBuffer());
    res.set('Content-Type', 'audio/mpeg');
    res.send(buffer);
  }
);

// --- Advance outreach (call next patient or send SMS) ---

export const advanceOutreach = onRequest(
  { cors: true },
  async (req, res) => {
    const { action, patientId } = req.body;

    if (action === 'no_answer') {
      // Mark patient as no_answer, send SMS
      await db.doc(`patients/${patientId}`).update({ status: 'no_answer' });
      await logActivity('📞', `${req.body.patientName} — no answer`, 'warning');

      // Send SMS (via Twilio in production)
      await db.doc(`patients/${patientId}`).update({ status: 'sms_sent' });
      await db.doc('agent/status').update({ phase: 'sms_sent' });
      await logActivity('💬', `SMS sent to ${req.body.patientName}`, 'sms');

      res.json({ next: 'sms_sent' });
    } else if (action === 'sms_reply_yes') {
      // Patient confirmed
      await db.doc(`patients/${patientId}`).update({ status: 'confirmed' });
      await db.doc('agent/status').update({ phase: 'booking' });
      await db.doc('slots/active').update({ status: 'booking' });
      await logActivity('💬', `${req.body.patientName}: "Yes, that works!"`, 'success');

      // Finalize booking
      setTimeout(async () => {
        await db.doc('agent/status').update({ phase: 'filled' });
        await db.doc('slots/active').update({
          status: 'filled',
          bookedBy: req.body.patientName,
        });
        await logActivity('✅', `Slot filled! ${req.body.patientName} booked`, 'success');
      }, 2000);

      res.json({ next: 'booking' });
    } else if (action === 'skip') {
      // Skip to next patient
      await db.doc(`patients/${patientId}`).update({ status: 'skipped' });

      const next = await db.collection('patients')
        .where('status', '==', 'queued')
        .orderBy('order')
        .limit(1)
        .get();

      if (next.empty) {
        await db.doc('agent/status').update({ phase: 'idle' });
        await logActivity('❌', 'All patients contacted — slot unfilled', 'warning');
        res.json({ next: 'exhausted' });
      } else {
        const p = next.docs[0];
        await p.ref.update({ status: 'calling' });
        await db.doc('agent/status').update({
          phase: 'calling',
          currentPatient: p.data().name,
          attempt: FieldValue.increment(1),
        });
        await logActivity('📞', `Calling ${p.data().name}...`, 'call');
        res.json({ next: 'calling', patient: p.data().name });
      }
    } else {
      res.status(400).json({ error: 'Unknown action' });
    }
  }
);

// --- Trigger demo (seed data + start) ---

export const triggerDemo = onRequest(
  { cors: true },
  async (_req, res) => {
    // Clear old data
    const logs = await db.collection('activity_log').get();
    const batch = db.batch();
    logs.docs.forEach(d => batch.delete(d.ref));
    await batch.commit();

    // Seed patients
    const patients = [
      { name: 'Sarah Chen',     lastCleaning: '8 months ago', phone: '(555) 012-3456' },
      { name: 'James Patel',    lastCleaning: '7 months ago', phone: '(555) 234-5678' },
      { name: 'Maria Santos',   lastCleaning: '7 months ago', phone: '(555) 345-6789' },
      { name: 'Tom Bradley',    lastCleaning: '6 months ago', phone: '(555) 456-7890' },
      { name: 'Emma Liu',       lastCleaning: '6 months ago', phone: '(555) 567-8901' },
      { name: 'David Kim',      lastCleaning: '5 months ago', phone: '(555) 678-9012' },
      { name: 'Lisa Thompson',  lastCleaning: '5 months ago', phone: '(555) 789-0123' },
      { name: 'Ryan Garcia',    lastCleaning: '4 months ago', phone: '(555) 890-1234' },
    ];

    for (let i = 0; i < patients.length; i++) {
      await db.doc(`patients/p${i}`).set({
        ...patients[i],
        status: 'queued',
        order: i,
      });
    }

    await db.doc('slots/active').set({
      patientName: 'Marcus Webb',
      slotTime: '2:30 PM',
      slotDate: new Date().toISOString().split('T')[0],
      duration: 60,
      estimatedRevenue: 185,
      status: 'open',
    });

    await db.doc('agent/status').set({
      phase: 'idle',
      currentPatient: '',
      attempt: 0,
      totalPatients: 8,
    });

    res.json({ success: true });
  }
);
