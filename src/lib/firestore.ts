import {
  collection,
  doc,
  setDoc,
  addDoc,
  updateDoc,
  onSnapshot,
  query,
  orderBy,
  serverTimestamp,
  Timestamp,
} from 'firebase/firestore';
import { db } from './firebase';

// --- Types ---

export interface SlotDoc {
  patientName: string;
  slotTime: string;
  slotDate: string;
  duration: number;
  estimatedRevenue: number;
  status: 'open' | 'booking' | 'filled';
  bookedBy?: string;
}

export interface PatientDoc {
  name: string;
  phone: string;
  lastCleaning: string;
  status: 'queued' | 'calling' | 'no_answer' | 'sms_sent' | 'confirmed' | 'skipped';
  order: number;
}

export interface LogDoc {
  icon: string;
  message: string;
  type: 'call' | 'sms' | 'system' | 'success' | 'warning';
  timestamp: Timestamp;
}

export interface AgentDoc {
  phase: string;
  currentPatient: string;
  attempt: number;
  totalPatients: number;
}

// --- Seed data (for demo) ---

export async function seedDemoData() {
  // Active slot
  await setDoc(doc(db, 'slots', 'active'), {
    patientName: 'Marcus Webb',
    slotTime: '2:30 PM',
    slotDate: new Date().toISOString().split('T')[0],
    duration: 60,
    estimatedRevenue: 185,
    status: 'open',
  });

  // Agent status
  await setDoc(doc(db, 'agent', 'status'), {
    phase: 'idle',
    currentPatient: '',
    attempt: 0,
    totalPatients: 8,
  });

  // Patients
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
    await setDoc(doc(db, 'patients', `p${i}`), {
      ...patients[i],
      status: 'queued',
      order: i,
    });
  }

  // Initial log
  await addDoc(collection(db, 'activity_log'), {
    icon: '⚠️',
    message: 'Cancellation received — Marcus Webb',
    type: 'warning',
    timestamp: serverTimestamp(),
  });
}

// --- Real-time listeners ---

export function onSlotChange(cb: (slot: SlotDoc) => void) {
  return onSnapshot(doc(db, 'slots', 'active'), (snap) => {
    if (snap.exists()) cb(snap.data() as SlotDoc);
  });
}

export function onAgentChange(cb: (agent: AgentDoc) => void) {
  return onSnapshot(doc(db, 'agent', 'status'), (snap) => {
    if (snap.exists()) cb(snap.data() as AgentDoc);
  });
}

export function onPatientsChange(cb: (patients: PatientDoc[]) => void) {
  const q = query(collection(db, 'patients'), orderBy('order'));
  return onSnapshot(q, (snap) => {
    cb(snap.docs.map(d => d.data() as PatientDoc));
  });
}

export function onLogsChange(cb: (logs: LogDoc[]) => void) {
  const q = query(collection(db, 'activity_log'), orderBy('timestamp', 'desc'));
  return onSnapshot(q, (snap) => {
    cb(snap.docs.map(d => d.data() as LogDoc));
  });
}

// --- Write helpers ---

export async function updateSlot(data: Partial<SlotDoc>) {
  await updateDoc(doc(db, 'slots', 'active'), data);
}

export async function updateAgent(data: Partial<AgentDoc>) {
  await updateDoc(doc(db, 'agent', 'status'), data);
}

export async function updatePatient(id: string, data: Partial<PatientDoc>) {
  await updateDoc(doc(db, 'patients', id), data);
}

export async function addLog(icon: string, message: string, type: LogDoc['type']) {
  await addDoc(collection(db, 'activity_log'), {
    icon,
    message,
    type,
    timestamp: serverTimestamp(),
  });
}
