import { useRef, useCallback, useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  morphPath,
  createSprings,
  tickSprings,
  readState,
} from './animationEngine';
import type { MorphTarget, MorphState, AnimSprings } from './animationEngine';

type MenuItem =
  | { label: string; action?: string; accent?: boolean }
  | { sep: true };

const NAV_ITEMS: MenuItem[] = [
  { label: 'Dashboard' },
  { sep: true },
  { label: 'Patients' },
  { label: 'Activity Log' },
  { sep: true },
  { label: 'Add Mock Data', action: 'seed', accent: true },
  { label: 'Settings' },
];

const PILL_W = 100, PILL_H = 36;
const MENU_W = 210, MENU_H = 260, MENU_R = 16;

interface Props {
  onAction?: (action: string) => void;
}

export function MenuPill({ onAction }: Props) {
  const pathRef = useRef<SVGPathElement>(null);
  const glowRef = useRef<SVGPathElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const pillRef = useRef<HTMLButtonElement>(null);
  const rafRef = useRef(0);
  const lastTimeRef = useRef(0);
  const springsRef = useRef<AnimSprings | null>(null);
  const targetRef = useRef<MorphTarget | null>(null);
  const menuBouncedRef = useRef(false);

  const [pillHidden, setPillHidden] = useState(false);
  const [overlayActive, setOverlayActive] = useState(false);

  const apply = useCallback((s: MorphState) => {
    const path = pathRef.current;
    const glow = glowRef.current;
    const menu = menuRef.current;
    if (!path || !glow || !menu) return;

    const d = morphPath(s.cx, s.cy, s.width, s.height, s.cornerRadius);
    path.setAttribute('d', d);
    glow.setAttribute('d', d);
    path.removeAttribute('transform');
    glow.removeAttribute('transform');
    glow.setAttribute('opacity', '0');
    path.style.filter = 'drop-shadow(0 2px 12px rgba(0,0,0,0.12))';

    const top = s.cy - s.height / 2;
    const left = s.cx - s.width / 2;
    menu.style.cssText = `
      position:fixed;
      top:${top}px; left:${left}px;
      width:${s.width}px; height:${s.height}px;
      opacity:${s.contentOpacity};
      border-radius:${s.cornerRadius}px;
      overflow:hidden;
      pointer-events:${s.contentOpacity > 0.5 ? 'all' : 'none'};
    `;
  }, []);

  const loop = useCallback((now: number) => {
    const springs = springsRef.current;
    const target = targetRef.current;
    if (!springs || !target) return;

    const dt = Math.min((now - lastTimeRef.current) / 1000, 0.033);
    lastTimeRef.current = now;

    const finished = tickSprings(springs, dt, target);
    const reverseSnap = springs.direction === 'reverse' && !finished && springs.shape.v < 0.15;

    if (reverseSnap || (finished && springs.direction === 'reverse')) {
      pathRef.current?.setAttribute('d', '');
      glowRef.current?.setAttribute('d', '');
      if (menuRef.current) menuRef.current.style.opacity = '0';
      if (pillRef.current) {
        pillRef.current.style.opacity = '1';
        pillRef.current.style.pointerEvents = 'auto';
      }
      setPillHidden(false);
      setOverlayActive(false);
      springsRef.current = null;

      pillRef.current?.animate([
        { transform: 'scale(0.88)', offset: 0 },
        { transform: 'scale(1.1)', offset: 0.4 },
        { transform: 'scale(0.96)', offset: 0.7 },
        { transform: 'scale(1.02)', offset: 0.88 },
        { transform: 'scale(1)', offset: 1 },
      ], { duration: 400, easing: 'ease-out' });
      return;
    }

    const state = readState(springs, target);
    apply(state);

    if (springs.direction === 'forward' && !menuBouncedRef.current && springs.shape.v > 0.85) {
      menuBouncedRef.current = true;
      menuRef.current?.animate([
        { transform: 'scale(0.97)', offset: 0 },
        { transform: 'scale(1.025)', offset: 0.4 },
        { transform: 'scale(0.995)', offset: 0.7 },
        { transform: 'scale(1)', offset: 1 },
      ], { duration: 350, easing: 'ease-out' });
    }

    if (finished) {
      springsRef.current = null;
      return;
    }

    rafRef.current = requestAnimationFrame(loop);
  }, [apply]);

  const getTarget = useCallback((): MorphTarget => {
    const r = pillRef.current!.getBoundingClientRect();
    return {
      pillLeft: r.left,
      pillRight: r.right,
      pillTop: r.top,
      pillCx: r.left + r.width / 2,
      pillCy: r.top + r.height / 2,
      pillWidth: PILL_W,
      pillHeight: PILL_H,
      menuWidth: MENU_W,
      menuHeight: MENU_H,
      menuRadius: MENU_R,
    };
  }, []);

  const open = useCallback(() => {
    if (springsRef.current) return;
    const target = getTarget();
    targetRef.current = target;
    setPillHidden(true);
    setOverlayActive(true);
    menuBouncedRef.current = false;
    cancelAnimationFrame(rafRef.current);

    springsRef.current = createSprings(target, 'forward');
    lastTimeRef.current = performance.now();
    rafRef.current = requestAnimationFrame(loop);
  }, [getTarget, loop]);

  const close = useCallback(() => {
    if (springsRef.current?.direction === 'reverse') return;
    const target = targetRef.current ?? getTarget();
    targetRef.current = target;
    cancelAnimationFrame(rafRef.current);

    springsRef.current = createSprings(target, 'reverse');
    lastTimeRef.current = performance.now();
    rafRef.current = requestAnimationFrame(loop);
  }, [getTarget, loop]);

  const onOverlayClick = useCallback((e: React.MouseEvent) => {
    const menu = menuRef.current;
    if (menu && parseFloat(menu.style.opacity || '0') > 0.5) {
      const r = menu.getBoundingClientRect();
      if (e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom) return;
    }
    close();
  }, [close]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close(); };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      cancelAnimationFrame(rafRef.current);
    };
  }, [close]);

  const handleItemClick = useCallback((item: MenuItem) => {
    if ('action' in item && item.action && onAction) {
      onAction(item.action);
    }
    close();
  }, [close, onAction]);

  const overlay = (
    <div
      onClick={overlayActive ? onOverlayClick : undefined}
      style={{
        position: 'fixed', inset: 0, zIndex: 100,
        pointerEvents: overlayActive ? 'all' : 'none',
      }}
    >
      <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0 }}>
        <path ref={glowRef} fill="none" stroke="rgba(0,0,0,0.06)" strokeWidth="12" opacity="0" style={{ filter: 'blur(8px)' }} />
        <path ref={pathRef} fill="rgba(255,255,255,0.98)" stroke="rgba(0,0,0,0.06)" strokeWidth="0.5" style={{ filter: 'drop-shadow(0 4px 24px rgba(0,0,0,0.12))' }} />
      </svg>

      <div ref={menuRef} style={{ position: 'fixed', opacity: 0, overflow: 'hidden', pointerEvents: 'none', borderRadius: MENU_R }}>
        <div style={{ padding: '8px' }}>
          {NAV_ITEMS.map((item, i) => {
            if ('sep' in item) {
              return <div key={i} style={{ height: 1, margin: '4px 12px', background: 'rgba(0,0,0,0.06)' }} />;
            }
            return (
              <div
                key={i}
                onClick={() => handleItemClick(item)}
                style={{
                  display: 'flex', alignItems: 'center',
                  padding: '10px 14px', cursor: 'pointer',
                  color: item.accent ? '#0097A7' : '#1d1d1f',
                  fontSize: 13.5,
                  fontWeight: item.accent ? 600 : 500,
                  borderRadius: 10, margin: '1px 0',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = item.accent ? 'rgba(125,249,255,0.08)' : 'rgba(0,0,0,0.04)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                {item.label}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  return (
    <>
      <button
        ref={pillRef}
        onClick={open}
        style={{
          width: PILL_W, height: PILL_H, borderRadius: PILL_H / 2,
          border: '1px solid rgba(0,0,0,0.08)',
          background: 'rgba(0,0,0,0.03)',
          color: '#1d1d1f', cursor: 'pointer', outline: 'none',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
          opacity: pillHidden ? 0 : 1,
          pointerEvents: pillHidden ? 'none' : 'auto',
          position: 'relative', zIndex: 20,
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.06)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.03)')}
      >
        <svg width="14" height="10" viewBox="0 0 14 10" fill="none">
          <rect y="0" width="14" height="1.5" rx="0.75" fill="rgba(0,0,0,0.5)"/>
          <rect y="4.25" width="14" height="1.5" rx="0.75" fill="rgba(0,0,0,0.5)"/>
          <rect y="8.5" width="14" height="1.5" rx="0.75" fill="rgba(0,0,0,0.5)"/>
        </svg>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#6e6e73', letterSpacing: '0.01em' }}>Menu</span>
      </button>
      {createPortal(overlay, document.body)}
    </>
  );
}
