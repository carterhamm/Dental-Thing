interface Props {
  status: 'open' | 'booking' | 'filled';
  bookedBy?: string;
  slotTime?: string;
}

export function CancellationSlot({ status, bookedBy, slotTime = '—' }: Props) {
  const isFilled = status === 'filled';
  const isBooking = status === 'booking';

  return (
    <div className={`bg-white rounded-2xl p-6 flex flex-col justify-between h-full border-l-4 transition-all duration-500 relative overflow-hidden ${
      isFilled ? 'border-l-green-500' : isBooking ? 'border-l-amber-400' : 'border-l-red-400'
    }`}
    style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 6px 16px rgba(0,0,0,0.04)' }}
    >
      {/* Subtle background tint */}
      {isFilled && <div className="absolute inset-0 bg-gradient-to-br from-green-50/60 to-transparent pointer-events-none" />}
      {!isFilled && !isBooking && <div className="absolute inset-0 bg-gradient-to-br from-red-50/30 to-transparent pointer-events-none" />}

      <div className="relative">
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] font-semibold tracking-[0.08em] text-gray-400 uppercase">
            Cancellation Slot
          </span>
          <div className="flex items-center gap-2">
            {status === 'open' && (
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-400" />
              </span>
            )}
            <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full transition-colors duration-500 ${
              isFilled
                ? 'bg-green-50 text-green-600 border border-green-100'
                : isBooking
                  ? 'bg-amber-50 text-amber-600 border border-amber-100'
                  : 'bg-red-50 text-red-500 border border-red-100'
            }`}>
              {isFilled ? 'FILLED' : isBooking ? 'BOOKING...' : 'OPEN'}
            </span>
          </div>
        </div>

        <div className="text-[32px] font-bold tracking-tight text-gray-900 mb-0.5">
          {slotTime}
        </div>
        <div className="text-gray-400 text-[13px]">
          Today &middot; 60 min cleaning
        </div>
      </div>

      <div className="relative mt-4 pt-4 border-t border-gray-100">
        {isFilled ? (
          <div className="flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-green-50 border border-green-200 flex items-center justify-center text-[10px]">✓</span>
            <span className="text-green-600 text-sm font-semibold">{bookedBy}</span>
          </div>
        ) : (
          <>
            <div className="text-gray-400 text-[11px] mb-0.5">Cancelled by</div>
            <div className="text-gray-700 text-sm font-medium">Marcus Webb</div>
          </>
        )}
        <div className="text-gray-300 text-[11px] mt-2">Est. revenue &middot; $185</div>
      </div>
    </div>
  );
}
