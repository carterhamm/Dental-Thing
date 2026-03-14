import { useState, useEffect, useCallback } from 'react';
import { MenuPill } from './components/MenuAnimation/MenuPill';
import { CancellationSlot } from './components/dashboard/CancellationSlot';
import { AgentStatus } from './components/dashboard/AgentStatus';
import type { AgentPhase } from './components/dashboard/AgentStatus';
import { PatientQueue } from './components/dashboard/PatientQueue';
import type { Patient } from './components/dashboard/PatientQueue';
import { ActivityLog } from './components/dashboard/ActivityLog';
import type { LogEntry } from './components/dashboard/ActivityLog';
import { StatsBar } from './components/dashboard/StatsBar';
import { onSessionChange } from './lib/firestore';
import type { SessionData } from './lib/firestore';

const BACKEND = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

// --- Mapping helpers: sessions/current → UI components ---

function mapSlotStatus(s?: string): 'open' | 'booking' | 'filled' {
  if (s === 'filled') return 'filled';
  if (s === 'filling') return 'booking';
  return 'open';
}

function mapCandidateStatus(s: string): Patient['status'] {
  switch (s) {
    case 'calling': return 'calling';
    case 'texting': return 'sms_sent';
    case 'no_answer': return 'no_answer';
    case 'declined': case 'no_reply': return 'skipped';
    case 'confirmed': return 'confirmed';
    default: return 'queued';
  }
}

function derivePhase(data: SessionData): AgentPhase {
  if (data.agent_status === 'complete' || data.slot?.status === 'filled') return 'filled';
  if (data.agent_status !== 'running') return 'idle';
  const active = (data.candidates || []).find(c => c.status === 'calling' || c.status === 'texting');
  if (active?.status === 'calling') return 'calling';
  if (active?.status === 'texting') return 'sms_sent';
  if ((data.candidates || []).some(c => c.status === 'confirmed')) return 'filled';
  return 'calling';
}

function getActivityIcon(type: string): string {
  if (type === 'call_outcome') return '📞';
  if (type === 'sms_sent') return '💬';
  if (type === 'success') return '✅';
  if (type === 'error') return '❌';
  if (type === 'thinking') return '🧠';
  if (type === 'tool_call') return '⚙️';
  return '📋';
}

function getActivityType(type: string): LogEntry['type'] {
  if (type === 'call_outcome') return 'call';
  if (type === 'sms_sent') return 'sms';
  if (type === 'success') return 'success';
  if (type === 'error') return 'warning';
  return 'system';
}

function formatTs(ts: string): string {
  try {
    const d = new Date(ts);
    const h = d.getHours();
    const m = d.getMinutes().toString().padStart(2, '0');
    return `${h > 12 ? h - 12 : h}:${m} ${h >= 12 ? 'PM' : 'AM'}`;
  } catch {
    return '';
  }
}

function now() {
  const d = new Date();
  const h = d.getHours();
  const m = d.getMinutes().toString().padStart(2, '0');
  return `${h > 12 ? h - 12 : h}:${m} ${h >= 12 ? 'PM' : 'AM'}`;
}

// Stat icons
const CheckIcon = () => <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 8.5L7 11.5L12 5" stroke="#22c55e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const DollarIcon = () => <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2v12M5 5.5c0-1.1.9-2 2-2h2.5c1.1 0 2 .9 2 2s-.9 2-2 2H6.5c-1.1 0-2 .9-2 2s.9 2 2 2H11" stroke="#6b7280" strokeWidth="1.5" strokeLinecap="round"/></svg>;
const PhoneIcon = () => <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 3.5C3 2.67 3.67 2 4.5 2H6l1.5 3-1.25.88a7 7 0 003.87 3.87L11 8.5l3 1.5v1.5c0 .83-.67 1.5-1.5 1.5A10.5 10.5 0 013 3.5z" stroke="#0097A7" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const MessageIcon = () => <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 4c0-.55.45-1 1-1h10c.55 0 1 .45 1 1v7c0 .55-.45 1-1 1H5l-3 3V4z" stroke="#9333ea" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/></svg>;

function App() {
  const [phase, setPhase] = useState<AgentPhase>('idle');
  const [patients, setPatients] = useState<Patient[]>([]);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [slotStatus, setSlotStatus] = useState<'open' | 'booking' | 'filled'>('open');
  const [slotTime, setSlotTime] = useState('—');
  const [slotFilledBy, setSlotFilledBy] = useState<string | undefined>();
  const [recovered, setRecovered] = useState(0);
  const [callCount, setCallCount] = useState(0);
  const [smsCount, setSmsCount] = useState(0);
  const [filledCount, setFilledCount] = useState(0);
  const [currentPatient, setCurrentPatient] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [totalPatients, setTotalPatients] = useState(0);
  const [triggering, setTriggering] = useState(false);

  // Listen to sessions/current — single source of truth from backend
  useEffect(() => {
    const unsub = onSessionChange((data) => {
      if (!data) return;

      // Slot
      setSlotStatus(mapSlotStatus(data.slot?.status));
      setSlotTime(data.slot?.time || '—');
      setSlotFilledBy(data.slot?.filled_by || undefined);

      // Agent phase
      setPhase(derivePhase(data));
      setRecovered(data.recovered || 0);

      // Candidates → patients
      const candidates = data.candidates || [];
      setTotalPatients(candidates.length);
      setPatients(candidates.map(c => ({
        name: c.name,
        phone: c.phone,
        lastCleaning: `${c.days_overdue}d overdue`,
        status: mapCandidateStatus(c.status),
      })));

      // Derive current patient + attempt
      const activeIdx = candidates.findIndex(c => c.status === 'calling' || c.status === 'texting');
      if (activeIdx >= 0) {
        setCurrentPatient(candidates[activeIdx].name);
        setAttempt(activeIdx + 1);
      } else {
        const lastTouched = candidates.findIndex(c => c.status !== 'waiting');
        setAttempt(lastTouched >= 0 ? lastTouched + 1 : 0);
        setCurrentPatient(lastTouched >= 0 ? candidates[lastTouched].name : '');
      }

      // Stats from candidates
      setCallCount(candidates.filter(c => c.status !== 'waiting').length);
      setSmsCount(candidates.filter(c => ['texting', 'no_reply'].includes(c.status)).length);
      setFilledCount(candidates.filter(c => c.status === 'confirmed').length);

      // Activity → log
      const activities = data.activity || [];
      setLog([...activities].reverse().map(a => ({
        time: formatTs(a.timestamp),
        icon: getActivityIcon(a.type),
        message: a.text,
        type: getActivityType(a.type),
      })));
    });
    return () => unsub();
  }, []);

  const triggerCancellation = useCallback(async () => {
    setTriggering(true);
    try {
      await fetch(`${BACKEND}/cancellation`, { method: 'POST' });
    } catch (e) {
      console.error('Failed to trigger cancellation:', e);
    } finally {
      setTimeout(() => setTriggering(false), 2000);
    }
  }, []);

  const handleMenuAction = useCallback(async (action: string) => {
    if (action === 'reset') {
      try {
        await fetch(`${BACKEND}/reset`, { method: 'POST' });
      } catch (e) {
        console.error('Failed to reset:', e);
      }
    }
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
        style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
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
            onClick={triggerCancellation}
            disabled={triggering || phase !== 'idle'}
            className={`text-[11px] font-semibold px-4 py-1.5 rounded-full transition-all ${
              triggering || phase !== 'idle'
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-[#7DF9FF] text-gray-900 hover:bg-[#5CE8F0] cursor-pointer'
            }`}
            style={phase === 'idle' && !triggering ? { boxShadow: '0 2px 8px rgba(125,249,255,0.4)' } : undefined}
          >
            {triggering ? 'Starting...' : 'Trigger Cancellation'}
          </button>
          <span className="text-[13px] text-gray-300 tabular-nums font-medium">{clock}</span>
        </div>
      </header>

      {/* Main Grid */}
      <main className="flex-1 px-5 pt-4 pb-5 overflow-hidden">
        <div className="h-full grid grid-cols-4 gap-4" style={{ gridTemplateRows: '80px 200px 1fr' }}>
          <StatsBar stats={[
            { label: 'Filled', value: filledCount, accent: 'green', icon: <CheckIcon /> },
            { label: 'Recovered', value: `$${recovered}`, accent: 'gray', icon: <DollarIcon /> },
            { label: 'Calls', value: callCount, accent: 'cyan', icon: <PhoneIcon /> },
            { label: 'Texts', value: smsCount, accent: 'purple', icon: <MessageIcon /> },
          ]} />

          <div className="col-span-2">
            <CancellationSlot status={slotStatus} bookedBy={slotFilledBy} slotTime={slotTime} />
          </div>
          <div className="col-span-2">
            <AgentStatus phase={phase} currentPatient={currentPatient} attempt={attempt} totalPatients={totalPatients} />
          </div>

          <div className="col-span-2"><PatientQueue patients={patients} /></div>
          <div className="col-span-2"><ActivityLog entries={log} /></div>
        </div>
      </main>
    </div>
  );
}

export default App;
