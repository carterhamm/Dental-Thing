interface Props {
  status: 'open' | 'booking' | 'filled';
  bookedBy?: string;
}

export function CancellationSlot({ status, bookedBy }: Props) {
  const isFilled = status === 'filled';
  const isBooking = status === 'booking';

  return (
    <div className={`bg-white rounded-2xl shadow-sm p-6 flex flex-col justify-between h-full border-l-4 transition-colors duration-500 ${
      isFilled ? 'border-l-green-500' : isBooking ? 'border-l-amber-400' : 'border-l-red-400'
    }`}>
      <div>
        <div className="flex items-center justify-between mb-4">
          <span className="text-[11px] font-semibold tracking-[0.08em] text-gray-400 uppercase">
            Cancellation Slot
          </span>
          <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full transition-colors duration-500 ${
            isFilled
              ? 'bg-green-50 text-green-600'
              : isBooking
                ? 'bg-amber-50 text-amber-600'
                : 'bg-red-50 text-red-500'
          }`}>
            {isFilled ? 'FILLED' : isBooking ? 'BOOKING...' : 'OPEN'}
          </span>
        </div>

        <div className="text-[32px] font-bold tracking-tight text-gray-900 mb-1">
          2:30 PM
        </div>
        <div className="text-gray-400 text-sm">
          Today &middot; 60 min cleaning
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100">
        {isFilled ? (
          <div className="text-green-600 text-sm font-semibold">
            Booked: {bookedBy}
          </div>
        ) : (
          <>
            <div className="text-gray-400 text-[11px] mb-0.5">Cancelled by</div>
            <div className="text-gray-700 text-sm font-medium">Marcus Webb</div>
          </>
        )}
        <div className="text-gray-300 text-xs mt-2">Est. revenue &middot; $185</div>
      </div>
    </div>
  );
}
