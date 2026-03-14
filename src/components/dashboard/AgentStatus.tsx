export type AgentPhase = 'idle' | 'calling' | 'no_answer' | 'sms_sent' | 'sms_reply' | 'booking' | 'filled';

interface Props {
  phase: AgentPhase;
  currentPatient: string;
  attempt: number;
  totalPatients: number;
}

const PHASE_CONFIG: Record<AgentPhase, { label: string; cls: string; dotCls: string; borderCls: string; desc: string }> = {
  idle:       { label: 'IDLE',        cls: 'text-gray-400',     dotCls: 'bg-gray-300',     borderCls: 'border-l-gray-200', desc: 'Waiting for cancellation...' },
  calling:    { label: 'CALLING',     cls: 'text-[#0097A7]',    dotCls: 'bg-[#7DF9FF]',    borderCls: 'border-l-[#7DF9FF]', desc: 'Voice call in progress...' },
  no_answer:  { label: 'NO ANSWER',   cls: 'text-amber-600',    dotCls: 'bg-amber-500',    borderCls: 'border-l-amber-400', desc: 'No answer — switching to SMS' },
  sms_sent:   { label: 'SMS SENT',    cls: 'text-purple-600',   dotCls: 'bg-purple-500',   borderCls: 'border-l-purple-500', desc: 'Waiting for text reply...' },
  sms_reply:  { label: 'REPLY RECV',  cls: 'text-[#0097A7]',    dotCls: 'bg-[#7DF9FF]',    borderCls: 'border-l-[#7DF9FF]', desc: 'Patient confirmed!' },
  booking:    { label: 'BOOKING',     cls: 'text-amber-600',    dotCls: 'bg-amber-500',    borderCls: 'border-l-amber-400', desc: 'Confirming appointment...' },
  filled:     { label: 'SLOT FILLED', cls: 'text-green-600',    dotCls: 'bg-green-500',    borderCls: 'border-l-green-500', desc: 'Appointment booked successfully' },
};

export function AgentStatus({ phase, currentPatient, attempt, totalPatients }: Props) {
  const cfg = PHASE_CONFIG[phase];
  const isActive = phase !== 'idle' && phase !== 'filled';
  const pct = totalPatients > 0 ? (attempt / totalPatients) * 100 : 0;

  if (phase === 'idle' && totalPatients === 0) {
    return (
      <div className="bg-white rounded-2xl p-6 flex flex-col items-center justify-center h-full border-l-4 border-l-gray-200"
        style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.04)' }}>
        <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center mb-3">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M10 6v4m0 4h.01" stroke="#d1d5db" strokeWidth="1.5" strokeLinecap="round"/><circle cx="10" cy="10" r="7" stroke="#d1d5db" strokeWidth="1.5"/></svg>
        </div>
        <span className="text-[13px] font-medium text-gray-400">Agent standing by</span>
        <span className="text-[11px] text-gray-300 mt-1">Trigger a cancellation to start outreach</span>
      </div>
    );
  }

  return (
    <div
      className={`bg-white rounded-2xl p-6 flex flex-col justify-between h-full border-l-4 transition-colors duration-500 ${cfg.borderCls}`}
      style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.04)' }}
    >
      <div>
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] font-semibold tracking-[0.08em] text-gray-400 uppercase">
            Agent Status
          </span>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${cfg.dotCls} ${isActive ? 'animate-pulse' : ''}`} />
            <span className={`text-[11px] font-bold ${cfg.cls}`}>{cfg.label}</span>
          </div>
        </div>

        {phase !== 'idle' ? (
          <>
            <div className="text-gray-900 text-lg font-semibold mb-1">{currentPatient}</div>
            <div className="text-gray-400 text-[13px]">{cfg.desc}</div>
            {phase === 'calling' && (
              <div className="flex items-center gap-1 mt-3">
                {[0, 1, 2, 3, 4].map(i => (
                  <div
                    key={i}
                    className="w-1 rounded-full bg-[#7DF9FF]"
                    style={{
                      height: `${8 + Math.sin(i * 1.2) * 8}px`,
                      animation: `shimmer ${0.6 + i * 0.15}s ease-in-out infinite`,
                      animationDelay: `${i * 0.1}s`,
                    }}
                  />
                ))}
                <span className="text-[10px] text-[#0097A7] ml-2 font-medium">Ringing...</span>
              </div>
            )}
          </>
        ) : (
          <div className="text-gray-300 text-[13px]">{cfg.desc}</div>
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="flex items-center justify-between text-[11px] text-gray-400 mb-2">
          <span>Outreach progress</span>
          <span className="tabular-nums font-medium">{attempt} / {totalPatients}</span>
        </div>
        <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700 relative"
            style={{
              width: `${pct}%`,
              background: 'linear-gradient(90deg, #7DF9FF, #5CE8F0)',
              boxShadow: pct > 0 ? '0 0 8px rgba(125,249,255,0.5)' : 'none',
            }}
          />
        </div>
      </div>
    </div>
  );
}
