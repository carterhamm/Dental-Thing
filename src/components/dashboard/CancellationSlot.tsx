import { IconClock } from '../Icons';

interface Props {
  status: 'open' | 'booking' | 'filled';
  bookedBy?: string;
  slotTime?: string;
}

export function CancellationSlot({ status, bookedBy, slotTime = '—' }: Props) {
  const isFilled = status === 'filled';
  const isBooking = status === 'booking';
  const isEmpty = slotTime === '—';

  if (isEmpty) {
    return (
      <div className="bg-white rounded-2xl p-6 flex flex-col items-center justify-center h-full border border-dashed border-slate-200"
        style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
        <div className="w-14 h-14 rounded-2xl bg-slate-50 flex items-center justify-center mb-4 text-slate-300">
          <IconClock />
        </div>
        <span className="text-[14px] font-semibold text-slate-400">No cancellations</span>
        <span className="text-[12px] text-slate-300 mt-1 text-center">Slots will appear here when<br/>a patient cancels</span>
      </div>
    );
  }

  return (
    <div className={`rounded-2xl p-6 flex flex-col justify-between h-full relative overflow-hidden transition-all duration-500 ${
      isFilled ? 'bg-gradient-to-br from-emerald-50 via-white to-emerald-50/30 border border-emerald-200/60'
        : isBooking ? 'bg-gradient-to-br from-amber-50 via-white to-amber-50/30 border border-amber-200/60'
        : 'bg-gradient-to-br from-red-50 via-white to-[#E0FCFF]/20 border border-red-200/40'
    }`}
    style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 8px 20px rgba(0,0,0,0.04)' }}
    >
      {/* Accent corner glow */}
      <div className={`absolute -top-12 -right-12 w-32 h-32 rounded-full blur-3xl opacity-30 ${
        isFilled ? 'bg-emerald-300' : isBooking ? 'bg-amber-300' : 'bg-[#7DF9FF]'
      }`} />

      <div className="relative">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              isFilled ? 'bg-emerald-100 text-emerald-600' : isBooking ? 'bg-amber-100 text-amber-600' : 'bg-red-100 text-red-500'
            }`}>
              <IconClock />
            </div>
            <span className="text-[12px] font-semibold text-slate-500 uppercase tracking-[0.06em]">
              Cancellation Slot
            </span>
          </div>
          <div className="flex items-center gap-2">
            {status === 'open' && (
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-400" />
              </span>
            )}
            <span className={`text-[11px] font-bold px-3 py-1 rounded-full ${
              isFilled ? 'bg-emerald-100 text-emerald-700' : isBooking ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-600'
            }`}>
              {isFilled ? 'FILLED' : isBooking ? 'BOOKING...' : 'OPEN'}
            </span>
          </div>
        </div>

        <div className="text-[36px] font-bold tracking-tight text-slate-900 mb-1 font-mono">{slotTime}</div>
        <div className="text-slate-400 text-[13px] font-medium">Today &middot; 60 min cleaning</div>
      </div>

      <div className="relative mt-5 pt-4 border-t border-slate-100">
        {isFilled ? (
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M3 7.5l3 3 5-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>
            </div>
            <div>
              <div className="text-emerald-700 text-[13px] font-semibold">{bookedBy}</div>
              <div className="text-emerald-500/60 text-[11px]">Appointment confirmed</div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-slate-400 text-[11px] font-medium mb-0.5">Cancelled by</div>
              <div className="text-slate-700 text-[14px] font-semibold">Marcus Webb</div>
            </div>
            <div className="text-right">
              <div className="text-slate-400 text-[11px] font-medium mb-0.5">Revenue at risk</div>
              <div className="text-[#006B7A] text-[14px] font-bold font-mono">$185</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
