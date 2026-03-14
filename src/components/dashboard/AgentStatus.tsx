export type AgentPhase = 'idle' | 'calling' | 'no_answer' | 'sms_sent' | 'sms_reply' | 'booking' | 'filled';

interface Props {
  phase: AgentPhase;
  currentPatient: string;
  attempt: number;
  totalPatients: number;
}

const PHASE_CONFIG: Record<AgentPhase, { label: string; cls: string; dotCls: string; borderCls: string }> = {
  idle:       { label: 'IDLE',        cls: 'text-gray-400',     dotCls: 'bg-gray-300',     borderCls: 'border-l-gray-200' },
  calling:    { label: 'CALLING',     cls: 'text-[#0097A7]',    dotCls: 'bg-[#7DF9FF]',    borderCls: 'border-l-[#7DF9FF]' },
  no_answer:  { label: 'NO ANSWER',   cls: 'text-amber-600',    dotCls: 'bg-amber-500',    borderCls: 'border-l-amber-400' },
  sms_sent:   { label: 'SMS SENT',    cls: 'text-purple-600',   dotCls: 'bg-purple-500',   borderCls: 'border-l-purple-500' },
  sms_reply:  { label: 'REPLY RECV',  cls: 'text-teal-600',     dotCls: 'bg-teal-500',     borderCls: 'border-l-teal-500' },
  booking:    { label: 'BOOKING',     cls: 'text-amber-600',    dotCls: 'bg-amber-500',    borderCls: 'border-l-amber-400' },
  filled:     { label: 'SLOT FILLED', cls: 'text-green-600',    dotCls: 'bg-green-500',    borderCls: 'border-l-green-500' },
};

export function AgentStatus({ phase, currentPatient, attempt, totalPatients }: Props) {
  const cfg = PHASE_CONFIG[phase];
  const isActive = phase !== 'idle' && phase !== 'filled';

  return (
    <div className={`bg-white rounded-2xl shadow-sm p-6 flex flex-col justify-between h-full border-l-4 transition-colors duration-500 ${cfg.borderCls}`}>
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
            <div className="text-gray-400 text-sm">
              {phase === 'calling' && 'Voice call in progress...'}
              {phase === 'no_answer' && 'No answer — switching to SMS'}
              {phase === 'sms_sent' && 'Waiting for text reply...'}
              {phase === 'sms_reply' && 'Patient confirmed!'}
              {phase === 'booking' && 'Confirming appointment...'}
              {phase === 'filled' && 'Appointment booked successfully'}
            </div>
          </>
        ) : (
          <div className="text-gray-300 text-sm">Waiting for cancellation...</div>
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="flex items-center justify-between text-xs text-gray-400 mb-2">
          <span>Outreach progress</span>
          <span className="tabular-nums">{attempt} / {totalPatients}</span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full rounded-full bg-[#7DF9FF] transition-all duration-700"
            style={{ width: `${totalPatients > 0 ? (attempt / totalPatients) * 100 : 0}%` }}
          />
        </div>
      </div>
    </div>
  );
}
