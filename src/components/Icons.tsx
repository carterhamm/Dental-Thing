// Custom icon pack — consistent 20x20 stroke icons for DentAI

const S = { strokeWidth: 1.5, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none' };

export const IconTooth = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <path d="M6.5 3.5c-1.5 0-2.5 1.2-2.5 2.7 0 1.4.6 3 1.1 4.3.6 1.4 1.1 2.8 1.1 4.2 0 .7.5 1.3 1.1 1.3s1-.5 1-1.2l.2-2.3c.1-.5.5-.9 1-.9h1c.5 0 .9.4 1 .9l.2 2.3c0 .7.5 1.2 1 1.2.7 0 1.2-.6 1.2-1.3 0-1.4.5-2.8 1-4.2.6-1.3 1.2-2.9 1.2-4.3 0-1.5-1-2.7-2.5-2.7-.8 0-1.4.4-2 .7-.6.3-1.2.5-1.6.5s-1-.2-1.5-.5c-.6-.3-1.3-.7-2-.7z" stroke="currentColor" {...S}/>
  </svg>
);

export const IconClock = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <circle cx="10" cy="10" r="7.5" stroke="currentColor" {...S}/>
    <path d="M10 5.5v5l3.5 2" stroke="currentColor" {...S}/>
  </svg>
);

export const IconBot = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <rect x="3" y="6" width="14" height="10" rx="3" stroke="currentColor" {...S}/>
    <circle cx="7.5" cy="11" r="1.25" fill="currentColor"/>
    <circle cx="12.5" cy="11" r="1.25" fill="currentColor"/>
    <path d="M10 3v3M7 3h6" stroke="currentColor" {...S}/>
  </svg>
);

export const IconUsers = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <circle cx="7.5" cy="6.5" r="2.5" stroke="currentColor" {...S}/>
    <path d="M2.5 16.5c0-2.5 2.2-4.5 5-4.5s5 2 5 4.5" stroke="currentColor" {...S}/>
    <circle cx="14" cy="7" r="2" stroke="currentColor" {...S}/>
    <path d="M14.5 12c1.5.4 3 1.8 3 3.5" stroke="currentColor" {...S}/>
  </svg>
);

export const IconActivity = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <path d="M2.5 10h3.5l2-5 3 10 2-5h4.5" stroke="currentColor" {...S}/>
  </svg>
);

export const IconPhone = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <path d="M3.5 4.5c0-1 .7-1.5 1.5-1.5h1.5l2 3.5-1.5 1c.8 1.8 2.5 3.5 4.3 4.3l1-1.5L16 12.5V14c0 .8-.5 1.5-1.5 1.5C8 15.5 4.5 12 3.5 5.5v-1z" stroke="currentColor" {...S}/>
  </svg>
);

export const IconMessage = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <path d="M3 5c0-.55.45-1 1-1h12c.55 0 1 .45 1 1v8c0 .55-.45 1-1 1H6.5L3 17V5z" stroke="currentColor" {...S}/>
    <path d="M7 8h6M7 11h4" stroke="currentColor" {...S}/>
  </svg>
);

export const IconCheck = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <path d="M4.5 10.5l4 4 7-8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
  </svg>
);

export const IconDollar = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <path d="M10 2.5v15M6 7c0-1.4 1.3-2.5 3-2.5h2.5c1.4 0 2.5 1.1 2.5 2.5s-1.1 2.5-2.5 2.5H8c-1.4 0-2.5 1.1-2.5 2.5s1.1 2.5 2.5 2.5h3c1.7 0 3-1.1 3-2.5" stroke="currentColor" {...S}/>
  </svg>
);

export const IconAlert = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <path d="M10 6.5v4M10 14h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none"/>
    <path d="M8.6 3.6L2.4 14.2c-.7 1.2.2 2.8 1.5 2.8h12.2c1.3 0 2.2-1.6 1.5-2.8L11.4 3.6c-.7-1.2-2.1-1.2-2.8 0z" stroke="currentColor" {...S}/>
  </svg>
);

export const IconSettings = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <circle cx="10" cy="10" r="2.5" stroke="currentColor" {...S}/>
    <path d="M10 2.5v2M10 15.5v2M3.5 6l1.7 1M14.8 13l1.7 1M2.5 10h2M15.5 10h2M3.5 14l1.7-1M14.8 7l1.7-1" stroke="currentColor" {...S}/>
  </svg>
);

export const IconDatabase = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <ellipse cx="10" cy="5" rx="6.5" ry="2.5" stroke="currentColor" {...S}/>
    <path d="M3.5 5v5c0 1.38 2.91 2.5 6.5 2.5s6.5-1.12 6.5-2.5V5" stroke="currentColor" {...S}/>
    <path d="M3.5 10v5c0 1.38 2.91 2.5 6.5 2.5s6.5-1.12 6.5-2.5v-5" stroke="currentColor" {...S}/>
  </svg>
);

export const IconRefresh = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <path d="M3.5 3.5v4.5H8M16.5 16.5v-4.5H12" stroke="currentColor" {...S}/>
    <path d="M5.2 13A6.5 6.5 0 0116.5 8M14.8 7A6.5 6.5 0 013.5 12" stroke="currentColor" {...S}/>
  </svg>
);

export const IconWave = ({ className = '' }) => (
  <svg width="20" height="20" viewBox="0 0 20 20" className={className}>
    <path d="M2 10c1-3 2-6 3.5-6S8 13 10 13s3-6 4.5-6S17 7 18 10" stroke="currentColor" {...S}/>
  </svg>
);
