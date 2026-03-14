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
  onSlotChange,
  onAgentChange,
  onPatientsChange,
  onLogsChange,
  updateSlot,
  updateAgent,
  updatePatient as updatePatientDoc,
  addLog as addFirestoreLog,
} from './lib/firestore';

const INITIAL_PATIENTS: Patient[] = [
  { name: 'Sarah Chen',     lastCleaning: '8 months ago', phone: '(555) 012-3456', status: 'queued' },
  { name: 'James Patel',    lastCleaning: '7 months ago', phone: '(555) 234-5678', status: 'queued' },
  { name: 'Maria Santos',   lastCleaning: '7 months ago', phone: '(555) 345-6789', status: 'queued' },
  { name: 'Tom Bradley',    lastCleaning: '6 months ago', phone: '(555) 456-7890', status: 'queued' },
  { name: 'Emma Liu',       lastCleaning: '6 months ago', phone: '(555) 567-8901', status: 'queued' },
  { name: 'David Kim',      lastCleaning: '5 months ago', phone: '(555) 678-9012', status: 'queued' },
  { name: 'Lisa Thompson',  lastCleaning: '5 months ago', phone: '(555) 789-0123', status: 'queued' },
  { name: 'Ryan Garcia',    lastCleaning: '4 months ago', phone: '(555) 890-1234', status: 'queued' },
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

  // Firestore real-time listeners (always on)
  useEffect(() => {
    const unsubs = [
      onSlotChange((slot) => setSlotStatus(slot.status)),
      onAgentChange((agent) => {
        setPhase(agent.phase as AgentPhase);
        setAttempt(agent.attempt);
      }),
      onPatientsChange((pts) => {
        setPatients(pts.map(p => ({
          name: p.name, lastCleaning: p.lastCleaning, phone: p.phone,
          status: p.status as Patient['status'],
        })));
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
          updatePatientDoc('p0', { status: 'calling' }).catch(() => {});
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
          updatePatientDoc('p0', { status: 'no_answer' }).catch(() => {});
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
          updatePatientDoc('p0', { status: 'sms_sent' }).catch(() => {});
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
          updatePatientDoc('p0', { status: 'confirmed' }).catch(() => {});
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
    <div className="h-screen flex flex-col bg-[#f2f2f7]">
      {/* Header */}
      <header className="flex items-center justify-between px-5 h-14 shrink-0 border-b border-gray-200/80 bg-white/80 backdrop-blur-xl">
        <div className="flex items-center gap-4">
          <MenuPill />
          <span className="text-[15px] font-semibold text-gray-900 tracking-tight">DentAI</span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={runDemo}
            disabled={demoRunning}
            className={`text-[11px] font-semibold px-4 py-1.5 rounded-full transition-all ${
              demoRunning
                ? 'bg-[#7DF9FF]/30 text-[#0097A7] cursor-not-allowed'
                : 'bg-[#7DF9FF] text-gray-900 hover:bg-[#5CE8F0] cursor-pointer shadow-sm'
            }`}
          >
            {demoRunning ? 'Running...' : 'Run Demo'}
          </button>
          <span className="text-[13px] text-gray-300 tabular-nums">{clock}</span>
        </div>
      </header>

      {/* Main Grid */}
      <main className="flex-1 p-5 overflow-hidden">
        <div className="h-full grid grid-cols-2 grid-rows-[200px_1fr_80px] gap-4">
          <CancellationSlot status={slotStatus} bookedBy="Sarah Chen" />
          <AgentStatus
            phase={phase}
            currentPatient={patients[0]?.name || ''}
            attempt={attempt}
            totalPatients={patients.length}
          />
          <PatientQueue patients={patients} />
          <ActivityLog entries={log} />
          <div className="col-span-2">
            <StatsBar stats={[
              { label: 'Slots Filled', value: filledToday, accent: 'green' },
              { label: 'Revenue', value: `$${revenue}`, accent: 'gray' },
              { label: 'Calls Made', value: calls, accent: 'cyan' },
              { label: 'Texts Sent', value: texts, accent: 'purple' },
            ]} />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
