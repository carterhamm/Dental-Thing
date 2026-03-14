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
import { onSessionChange, seedSessionData } from './lib/firestore';
import type { SessionData } from './lib/firestore';

const BACKEND = import.meta.env.VITE_BACKEND_URL || 'https://dental-agent-production.up.railway.app';

type View = 'dashboard' | 'patients' | 'activity' | 'settings';

// --- Mapping helpers ---
function mapSlotStatus(s?: string): 'open' | 'booking' | 'filled' {
  if (s === 'filled') return 'filled';
  if (s === 'filling') return 'booking';
  return 'open';
}

function mapCandidateStatus(s: string): Patient['status'] {
  const m: Record<string, Patient['status']> = {
    calling: 'calling', texting: 'sms_sent', no_answer: 'no_answer',
    declined: 'skipped', no_reply: 'skipped', confirmed: 'confirmed',
  };
  return m[s] || 'queued';
}

function derivePhase(data: SessionData): AgentPhase {
  if (data.agent_status === 'complete' || data.slot?.status === 'filled') return 'filled';
  if (data.agent_status !== 'running') return 'idle';
  const c = data.candidates || [];
  const a = c.find(x => x.status === 'calling' || x.status === 'texting');
  if (a?.status === 'calling') return 'calling';
  if (a?.status === 'texting') return 'sms_sent';
  if (c.some(x => x.status === 'confirmed')) return 'filled';
  return 'calling';
}

function actIcon(t: string) {
  return { call_outcome: '📞', sms_sent: '💬', success: '✅', error: '❌', thinking: '🧠', tool_call: '⚙️' }[t] || '📋';
}

function actType(t: string): LogEntry['type'] {
  return { call_outcome: 'call' as const, sms_sent: 'sms' as const, success: 'success' as const, error: 'warning' as const }[t] || 'system';
}

function fmtTs(ts: string) {
  try { const d = new Date(ts); const h = d.getHours(); return `${h > 12 ? h - 12 : h}:${d.getMinutes().toString().padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`; }
  catch { return ''; }
}

function now() {
  const d = new Date(), h = d.getHours(), m = d.getMinutes().toString().padStart(2, '0');
  return `${h > 12 ? h - 12 : h}:${m} ${h >= 12 ? 'PM' : 'AM'}`;
}

import { IconCheck, IconDollar, IconPhone, IconMessage, IconTooth } from './components/Icons';

function App() {
  const [view, setView] = useState<View>('dashboard');
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
  const [toast, setToast] = useState<{ msg: string; type: 'ok' | 'err' } | null>(null);

  const showToast = useCallback((msg: string, type: 'ok' | 'err' = 'ok') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // Firestore listener
  useEffect(() => {
    const unsub = onSessionChange((data) => {
      if (!data) return;
      setSlotStatus(mapSlotStatus(data.slot?.status));
      setSlotTime(data.slot?.time || '—');
      setSlotFilledBy(data.slot?.filled_by || undefined);
      setPhase(derivePhase(data));
      setRecovered(data.recovered || 0);
      const c = data.candidates || [];
      setTotalPatients(c.length);
      setPatients(c.map(x => ({
        name: x.name, phone: x.phone,
        lastCleaning: `${x.days_overdue}d overdue`,
        status: mapCandidateStatus(x.status),
      })));
      const ai = c.findIndex(x => x.status === 'calling' || x.status === 'texting');
      if (ai >= 0) { setCurrentPatient(c[ai].name); setAttempt(ai + 1); }
      else { const lt = c.findIndex(x => x.status !== 'waiting'); setAttempt(lt >= 0 ? lt + 1 : 0); setCurrentPatient(lt >= 0 ? c[lt].name : ''); }
      setCallCount(c.filter(x => x.status !== 'waiting').length);
      setSmsCount(c.filter(x => ['texting', 'no_reply'].includes(x.status)).length);
      setFilledCount(c.filter(x => x.status === 'confirmed').length);
      const acts = data.activity || [];
      setLog([...acts].reverse().map(a => ({ time: fmtTs(a.timestamp), icon: actIcon(a.type), message: a.text, type: actType(a.type) })));
    });
    return () => unsub();
  }, []);

  const triggerCancellation = useCallback(async () => {
    setTriggering(true);
    try {
      const res = await fetch(`${BACKEND}/cancellation`, { method: 'POST' });
      if (res.ok) { showToast('Agent started — filling cancellation slot', 'ok'); }
      else { showToast(`Backend error: ${res.status}`, 'err'); }
    } catch {
      showToast(`Cannot reach backend at ${BACKEND}`, 'err');
    } finally {
      setTimeout(() => setTriggering(false), 2000);
    }
  }, [showToast]);

  const handleMenuAction = useCallback(async (action: string) => {
    if (action === 'seed') {
      try { await seedSessionData(); showToast('Session data seeded to Firestore', 'ok'); }
      catch { showToast('Failed to seed — check Firebase console', 'err'); }
    }
    if (action === 'reset') {
      try { await fetch(`${BACKEND}/reset`, { method: 'POST' }); } catch {}
      try { await seedSessionData(); showToast('Agent reset', 'ok'); } catch {}
    }
  }, [showToast]);

  // Tab key cycles views
  const VIEWS: View[] = ['dashboard', 'patients', 'activity', 'settings'];
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Tab' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        setView(prev => {
          const idx = VIEWS.indexOf(prev);
          return VIEWS[e.shiftKey ? (idx - 1 + VIEWS.length) % VIEWS.length : (idx + 1) % VIEWS.length];
        });
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const [clock, setClock] = useState(now());
  useEffect(() => { const id = setInterval(() => setClock(now()), 10000); return () => clearInterval(id); }, []);

  return (
    <div className="h-screen flex flex-col" style={{ background: 'radial-gradient(ellipse at 15% 0%, rgba(125,249,255,0.1) 0%, transparent 50%), radial-gradient(ellipse at 85% 100%, rgba(125,249,255,0.06) 0%, transparent 50%), #f0f2f5' }}>
      {/* Header */}
      <header className="flex items-center justify-between px-6 h-14 shrink-0 bg-white/90 backdrop-blur-xl relative z-10"
        style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
        <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-[#7DF9FF] via-[#7DF9FF]/30 to-transparent" />
        <div className="flex items-center gap-4">
          <MenuPill onAction={handleMenuAction} onNavigate={(v) => setView(v as View)} activeView={view} />
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-[#7DF9FF] text-[#006B7A] flex items-center justify-center">
              <IconTooth />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-[16px] font-bold text-slate-900 tracking-tight">DentAI</span>
              <span className="text-[11px] text-slate-400 font-medium hidden sm:inline">Cancellation Recovery</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={triggerCancellation} disabled={triggering || phase !== 'idle'}
            className={`text-[11px] font-semibold px-4 py-1.5 rounded-full transition-all ${
              triggering || phase !== 'idle'
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-[#7DF9FF] text-gray-900 hover:bg-[#5CE8F0] cursor-pointer'
            }`}
            style={phase === 'idle' && !triggering ? { boxShadow: '0 2px 8px rgba(125,249,255,0.4)' } : undefined}>
            {triggering ? 'Starting...' : 'Trigger Cancellation'}
          </button>
          <span className="text-[12px] text-gray-300 font-mono tabular-nums">{clock}</span>
        </div>
      </header>

      {/* Toast */}
      {toast && (
        <div className="fixed top-16 left-1/2 -translate-x-1/2 z-50 animate-fadeIn">
          <div className={`px-4 py-2 rounded-xl text-[12px] font-medium shadow-lg backdrop-blur-sm ${
            toast.type === 'ok' ? 'bg-[#7DF9FF]/90 text-gray-900' : 'bg-red-500/90 text-white'
          }`}>{toast.msg}</div>
        </div>
      )}

      {/* Views */}
      <main className="flex-1 px-5 pt-4 pb-5 overflow-hidden">
        {view === 'dashboard' && (
          <div className="h-full grid grid-cols-4 gap-4 animate-fadeIn" style={{ gridTemplateRows: '88px minmax(240px, 1fr) minmax(0, 2fr)' }}>
            <StatsBar stats={[
              { label: 'Filled', value: filledCount, accent: 'green', icon: <IconCheck /> },
              { label: 'Recovered', value: `$${recovered}`, accent: 'gray', icon: <IconDollar /> },
              { label: 'Calls', value: callCount, accent: 'cyan', icon: <IconPhone /> },
              { label: 'Texts', value: smsCount, accent: 'purple', icon: <IconMessage /> },
            ]} />
            <div className="col-span-2"><CancellationSlot status={slotStatus} bookedBy={slotFilledBy} slotTime={slotTime} /></div>
            <div className="col-span-2"><AgentStatus phase={phase} currentPatient={currentPatient} attempt={attempt} totalPatients={totalPatients} /></div>
            <div className="col-span-2"><PatientQueue patients={patients} /></div>
            <div className="col-span-2"><ActivityLog entries={log} /></div>
          </div>
        )}

        {view === 'patients' && (
          <div className="h-full animate-fadeIn">
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-xl font-bold text-gray-900">Patient Queue</h1>
              <span className="text-[12px] text-gray-400 font-mono">{patients.length} patients</span>
            </div>
            <div className="h-[calc(100%-48px)]"><PatientQueue patients={patients} /></div>
          </div>
        )}

        {view === 'activity' && (
          <div className="h-full animate-fadeIn">
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-xl font-bold text-gray-900">Activity Log</h1>
              <span className="text-[12px] text-gray-400 font-mono">{log.length} events</span>
            </div>
            <div className="h-[calc(100%-48px)]"><ActivityLog entries={log} /></div>
          </div>
        )}

        {view === 'settings' && (
          <div className="max-w-2xl mx-auto pt-8 animate-fadeIn space-y-6">
            <h1 className="text-xl font-bold text-gray-900 mb-6">Settings</h1>

            <div className="bg-white rounded-2xl p-6" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.04)' }}>
              <h2 className="text-[11px] font-semibold tracking-[0.08em] text-gray-400 uppercase mb-4">Backend</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-[12px] text-gray-500 font-medium">API URL</label>
                  <div className="mt-1 px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 text-[13px] font-mono text-gray-700">{BACKEND}</div>
                </div>
                <p className="text-[11px] text-gray-400">Set <code className="bg-gray-100 px-1 py-0.5 rounded text-[10px]">VITE_BACKEND_URL</code> in your <code className="bg-gray-100 px-1 py-0.5 rounded text-[10px]">.env</code> file.</p>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.04)' }}>
              <h2 className="text-[11px] font-semibold tracking-[0.08em] text-gray-400 uppercase mb-4">Twilio Webhook</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-[12px] text-gray-500 font-medium">Messaging Webhook URL</label>
                  <div className="mt-1 px-3 py-2 rounded-lg bg-[#7DF9FF]/10 border border-[#7DF9FF]/20 text-[13px] font-mono text-[#0097A7]">
                    {BACKEND}/webhooks/twilio-sms
                  </div>
                </div>
                <div>
                  <label className="text-[12px] text-gray-500 font-medium">Voice Call Outcome Webhook</label>
                  <div className="mt-1 px-3 py-2 rounded-lg bg-[#7DF9FF]/10 border border-[#7DF9FF]/20 text-[13px] font-mono text-[#0097A7]">
                    {BACKEND}/call-outcome
                  </div>
                </div>
                <p className="text-[11px] text-gray-400">
                  Twilio Console → Phone Numbers → (385) 300-0856 → Messaging → "A message comes in" → paste the webhook URL above. Method: POST.
                </p>
              </div>
            </div>

            <div className="bg-white rounded-2xl p-6" style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.04)' }}>
              <h2 className="text-[11px] font-semibold tracking-[0.08em] text-gray-400 uppercase mb-4">Quick Actions</h2>
              <div className="flex gap-3">
                <button onClick={() => handleMenuAction('seed')}
                  className="px-4 py-2 rounded-xl bg-[#7DF9FF]/10 border border-[#7DF9FF]/20 text-[12px] font-semibold text-[#0097A7] hover:bg-[#7DF9FF]/20 transition-colors cursor-pointer">
                  Seed Data
                </button>
                <button onClick={() => handleMenuAction('reset')}
                  className="px-4 py-2 rounded-xl bg-red-50 border border-red-100 text-[12px] font-semibold text-red-500 hover:bg-red-100 transition-colors cursor-pointer">
                  Reset Agent
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
