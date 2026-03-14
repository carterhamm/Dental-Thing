import { useState, useEffect, useCallback, useRef } from 'react';
import { MenuPill } from './components/MenuAnimation/MenuPill';
import { CancellationSlot } from './components/dashboard/CancellationSlot';
import { AgentStatus } from './components/dashboard/AgentStatus';
import type { AgentPhase } from './components/dashboard/AgentStatus';
import { PatientQueue } from './components/dashboard/PatientQueue';
import type { Patient } from './components/dashboard/PatientQueue';
import { ActivityLog } from './components/dashboard/ActivityLog';
import type { LogEntry } from './components/dashboard/ActivityLog';
import { StatsBar } from './components/dashboard/StatsBar';
import { speak, stopSpeaking } from './lib/elevenlabs';
import {
  seedDemoData,
  seedMockPatients,
  onSlotChange,
  onAgentChange,
  onPatientsChange,
  onLogsChange,
  updateSlot,
  updateAgent,
  updatePatient as updatePatientDoc,
  addLog as addFirestoreLog,
  monthsAgo,
} from './lib/firestore';
import type { PatientDoc } from './lib/firestore';

const INITIAL_PATIENTS: Patient[] = [
  { name: 'Sarah Chen',     age: 36, lastCleaning: '8 months ago', phone: '(555) 012-3456', status: 'queued' },
  { name: 'James Patel',    age: 50, lastCleaning: '7 months ago', phone: '(555) 234-5678', status: 'queued' },
  { name: 'Maria Santos',   age: 28, lastCleaning: '7 months ago', phone: '(555) 345-6789', status: 'queued' },
  { name: 'Tom Bradley',    age: 45, lastCleaning: '6 months ago', phone: '(555) 456-7890', status: 'queued' },
  { name: 'Emma Liu',       age: 32, lastCleaning: '6 months ago', phone: '(555) 567-8901', status: 'queued' },
  { name: 'David Kim',      age: 61, lastCleaning: '5 months ago', phone: '(555) 678-9012', status: 'queued' },
  { name: 'Lisa Thompson',  age: 39, lastCleaning: '5 months ago', phone: '(555) 789-0123', status: 'queued' },
  { name: 'Ryan Garcia',    age: 26, lastCleaning: '4 months ago', phone: '(555) 890-1234', status: 'queued' },
];

const INITIAL_LOG: LogEntry[] = [
  { time: '2:45 PM', icon: '⚠️', message: 'Cancellation received — Marcus Webb', type: 'warning' },
];

function now() {
  const d = new Date();
  const h = d.getHours();
  const m = d.getMinutes().toString().padStart(2, '0');
  const ampm = h >= 12 ? 'PM' : 'AM';
  return `${h > 12 ? h - 12 : h}:${m} ${ampm}`;
}

function patientDocToPatient(p: PatientDoc): Patient {
  return {
    name: `${p.firstName} ${p.lastName}`,
    age: p.age,
    phone: p.phone,
    lastCleaning: monthsAgo(p.lastCleaning),
    status: p.outreachStatus as Patient['status'],
  };
}

// Stat icons as small SVGs
const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M4 8.5L7 11.5L12 5" stroke="#22c55e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);
const DollarIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M8 2v12M5 5.5c0-1.1.9-2 2-2h2.5c1.1 0 2 .9 2 2s-.9 2-2 2H6.5c-1.1 0-2 .9-2 2s.9 2 2 2H11" stroke="#6b7280" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);
const PhoneIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M3 3.5C3 2.67 3.67 2 4.5 2H6l1.5 3-1.25.88a7 7 0 003.87 3.87L11 8.5l3 1.5v1.5c0 .83-.67 1.5-1.5 1.5A10.5 10.5 0 013 3.5z" stroke="#0097A7" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);
const MessageIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M2 4c0-.55.45-1 1-1h10c.55 0 1 .45 1 1v7c0 .55-.45 1-1 1H5l-3 3V4z" stroke="#9333ea" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

function App() {
  const [phase, setPhase] = useState<AgentPhase>('idle');
  const [patients, setPatients] = useState<Patient[]>(INITIAL_PATIENTS);
  const [log, setLog] = useState<LogEntry[]>(INITIAL_LOG);
  const [slotStatus, setSlotStatus] = useState<'open' | 'booking' | 'filled'>('open');
  const [attempt, setAttempt] = useState(0);
  const [demoRunning, setDemoRunning] = useState(false);
  const [filledToday, setFilledToday] = useState(3);
  const [revenue, setRevenue] = useState(425);
  const [calls, setCalls] = useState(12);
  const [texts, setTexts] = useState(4);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  // Firestore real-time listeners
  useEffect(() => {
    const unsubs = [
      onSlotChange((slot) => setSlotStatus(slot.status)),
      onAgentChange((agent) => {
        setPhase(agent.phase as AgentPhase);
        setAttempt(agent.attempt);
      }),
      onPatientsChange((pts) => {
        setPatients(pts.map(patientDocToPatient));
      }),
      onLogsChange((logs) => {
        setLog(logs.map(l => ({
          time: l.timestamp?.toDate
            ? (() => { const d = l.timestamp.toDate(); const h = d.getHours(); return `${h > 12 ? h - 12 : h}:${d.getMinutes().toString().padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`; })()
            : now(),
          icon: l.icon, message: l.message, type: l.type,
        })));
      }),
    ];
    return () => unsubs.forEach(u => u());
  }, []);

  const addLocalLog = useCallback((entry: Omit<LogEntry, 'time'>) => {
    setLog(prev => [{ ...entry, time: now() }, ...prev]);
  }, []);

  const updateLocalPatient = useCallback((index: number, status: Patient['status']) => {
    setPatients(prev => prev.map((p, i) => i === index ? { ...p, status } : p));
  }, []);

  // Menu action handler
  const handleMenuAction = useCallback(async (action: string) => {
    if (action === 'seed') {
      try {
        await seedMockPatients();
        addLocalLog({ icon: '🗂️', message: 'Mock patient data added to Firestore', type: 'system' });
        addFirestoreLog('🗂️', 'Mock patient data seeded', 'system').catch(() => {});
      } catch {
        addLocalLog({ icon: '❌', message: 'Failed to seed data — check Firebase console', type: 'warning' });
      }
    }
  }, [addLocalLog]);

  const runDemo = useCallback(async () => {
    if (demoRunning) return;
    setDemoRunning(true);
    stopSpeaking();
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];

    setPatients(INITIAL_PATIENTS);
    setLog(INITIAL_LOG);
    setSlotStatus('open');
    setAttempt(0);
    setPhase('idle');

    seedDemoData().catch(() => {});

    const fireLog = async (icon: string, message: string, type: LogEntry['type']) => {
      addLocalLog({ icon, message, type });
      addFirestoreLog(icon, message, type).catch(() => {});
    };

    const steps: Array<{ delay: number; action: () => Promise<void> | void }> = [
      {
        delay: 800,
        action: async () => {
          setPhase('calling');
          setAttempt(1);
          updateLocalPatient(0, 'calling');
          await fireLog('📞', 'Calling Sarah Chen...', 'call');
          setCalls(c => c + 1);
          updateAgent({ phase: 'calling', currentPatient: 'Sarah Chen', attempt: 1 }).catch(() => {});
          updatePatientDoc('p0', { outreachStatus: 'calling' } as any).catch(() => {});
          speak(
            "Hi Sarah, this is the dental office calling. We had a cancellation today at 2:30 PM and wanted to see if you'd like to come in for your cleaning appointment. Would that work for you?"
          ).catch(() => {});
        },
      },
      {
        delay: 5000,
        action: async () => {
          setPhase('no_answer');
          updateLocalPatient(0, 'no_answer');
          await fireLog('📞', 'Sarah Chen — no answer', 'warning');
          updateAgent({ phase: 'no_answer' }).catch(() => {});
          updatePatientDoc('p0', { outreachStatus: 'no_answer' } as any).catch(() => {});
        },
      },
      {
        delay: 1500,
        action: async () => {
          setPhase('sms_sent');
          updateLocalPatient(0, 'sms_sent');
          await fireLog('💬', 'SMS sent to Sarah Chen: "Hi Sarah, we have an opening at 2:30 PM today for a cleaning. Would you like to book it?"', 'sms');
          setTexts(t => t + 1);
          updateAgent({ phase: 'sms_sent' }).catch(() => {});
          updatePatientDoc('p0', { outreachStatus: 'sms_sent' } as any).catch(() => {});
        },
      },
      {
        delay: 4000,
        action: async () => {
          setPhase('sms_reply');
          await fireLog('💬', 'Sarah Chen: "Yes, 2:30 works for me!"', 'success');
          speak("Great news. Sarah Chen replied yes, 2:30 works for me. Confirming the appointment now.").catch(() => {});
          updateAgent({ phase: 'sms_reply' }).catch(() => {});
        },
      },
      {
        delay: 2000,
        action: async () => {
          setPhase('booking');
          setSlotStatus('booking');
          updateLocalPatient(0, 'confirmed');
          await fireLog('📋', 'Confirming appointment...', 'system');
          updateAgent({ phase: 'booking' }).catch(() => {});
          updateSlot({ status: 'booking' }).catch(() => {});
          updatePatientDoc('p0', { outreachStatus: 'confirmed' } as any).catch(() => {});
        },
      },
      {
        delay: 2000,
        action: async () => {
          setPhase('filled');
          setSlotStatus('filled');
          setFilledToday(f => f + 1);
          setRevenue(r => r + 185);
          await fireLog('✅', 'Slot filled! Sarah Chen booked for 2:30 PM', 'success');
          setDemoRunning(false);
          updateAgent({ phase: 'filled' }).catch(() => {});
          updateSlot({ status: 'filled', bookedBy: 'Sarah Chen' }).catch(() => {});
        },
      },
    ];

    let totalDelay = 0;
    steps.forEach(step => {
      totalDelay += step.delay;
      const timer = setTimeout(() => step.action(), totalDelay);
      timersRef.current.push(timer);
    });
  }, [demoRunning, addLocalLog, updateLocalPatient]);

  useEffect(() => {
    return () => {
      timersRef.current.forEach(clearTimeout);
      stopSpeaking();
    };
  }, []);

  const [clock, setClock] = useState(now());
  useEffect(() => {
    const id = setInterval(() => setClock(now()), 10000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="h-screen flex flex-col" style={{ background: 'linear-gradient(160deg, #f2f2f7 0%, #f0f4f8 50%, rgba(125,249,255,0.04) 100%)' }}>
      {/* Header */}
      <header className="flex items-center justify-between px-6 h-14 shrink-0 bg-white/80 backdrop-blur-xl relative z-10"
        style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}
      >
        {/* Accent gradient line */}
        <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[#7DF9FF] via-[#7DF9FF]/40 to-transparent" />

        <div className="flex items-center gap-4">
          <MenuPill onAction={handleMenuAction} />
          <div className="flex items-baseline gap-2">
            <span className="text-[16px] font-bold text-gray-900 tracking-tight">DentAI</span>
            <span className="text-[11px] text-gray-400 font-medium hidden sm:inline">Cancellation Recovery</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={runDemo}
            disabled={demoRunning}
            className={`text-[11px] font-semibold px-4 py-1.5 rounded-full transition-all ${
              demoRunning
                ? 'bg-[#7DF9FF]/20 text-[#0097A7] cursor-not-allowed'
                : 'bg-[#7DF9FF] text-gray-900 hover:bg-[#5CE8F0] cursor-pointer'
            }`}
            style={!demoRunning ? { boxShadow: '0 2px 8px rgba(125,249,255,0.4)' } : undefined}
          >
            {demoRunning ? 'Running...' : 'Run Demo'}
          </button>
          <span className="text-[13px] text-gray-300 tabular-nums font-medium">{clock}</span>
        </div>
      </header>

      {/* Main Grid */}
      <main className="flex-1 px-5 pt-4 pb-5 overflow-hidden">
        <div className="h-full grid grid-cols-4 gap-4" style={{ gridTemplateRows: '80px 200px 1fr' }}>
          {/* Row 1: Stats */}
          <StatsBar stats={[
            { label: 'Slots Filled', value: filledToday, accent: 'green', icon: <CheckIcon /> },
            { label: 'Revenue', value: `$${revenue}`, accent: 'gray', icon: <DollarIcon /> },
            { label: 'Calls Made', value: calls, accent: 'cyan', icon: <PhoneIcon /> },
            { label: 'Texts Sent', value: texts, accent: 'purple', icon: <MessageIcon /> },
          ]} />

          {/* Row 2: Main Cards */}
          <div className="col-span-2">
            <CancellationSlot status={slotStatus} bookedBy="Sarah Chen" />
          </div>
          <div className="col-span-2">
            <AgentStatus
              phase={phase}
              currentPatient={patients[0]?.name || ''}
              attempt={attempt}
              totalPatients={patients.length}
            />
          </div>

          {/* Row 3: Lists */}
          <div className="col-span-2">
            <PatientQueue patients={patients} />
          </div>
          <div className="col-span-2">
            <ActivityLog entries={log} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
