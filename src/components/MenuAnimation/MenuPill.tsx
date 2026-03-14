import { useRef, useCallback, useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  morphPath, createSprings, tickSprings, readState,
} from './animationEngine';
import type { MorphTarget, MorphState, AnimSprings } from './animationEngine';

type MenuItem =
  | { label: string; view?: string; action?: string; accent?: boolean; danger?: boolean }
  | { sep: true };

const NAV_ITEMS: MenuItem[] = [
  { label: 'Dashboard', view: 'dashboard' },
  { sep: true },
  { label: 'Patients', view: 'patients' },
  { label: 'Activity Log', view: 'activity' },
  { sep: true },
  { label: 'Initialize Database', action: 'seed', accent: true },
  { label: 'Reset Agent', action: 'reset', danger: true },
  { sep: true },
  { label: 'Settings', view: 'settings' },
];

// Dynamic sizing
const PILL_W = 44, PILL_H = 40;
const MENU_W = 210, MENU_R = 16;
const ITEM_H = 40;
const SEP_H = 9;
const PAD = 16;
const MENU_H = NAV_ITEMS.reduce((h, item) => h + ('sep' in item ? SEP_H : ITEM_H), PAD);

interface Props {
  onAction?: (action: string) => void;
  onNavigate?: (view: string) => void;
  activeView?: string;
}

export function MenuPill({ onAction, onNavigate, activeView }: Props) {
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
    const path = pathRef.current, glow = glowRef.current, menu = menuRef.current;
    if (!path || !glow || !menu) return;
    const d = morphPath(s.cx, s.cy, s.width, s.height, s.cornerRadius);
    path.setAttribute('d', d);
    glow.setAttribute('d', d);
    path.removeAttribute('transform');
    glow.removeAttribute('transform');
    glow.setAttribute('opacity', '0');
    path.style.filter = 'drop-shadow(0 4px 24px rgba(0,0,0,0.12))';
    menu.style.cssText = `position:fixed;top:${s.cy - s.height / 2}px;left:${s.cx - s.width / 2}px;width:${s.width}px;height:${s.height}px;opacity:${s.contentOpacity};border-radius:${s.cornerRadius}px;overflow:hidden;pointer-events:${s.contentOpacity > 0.5 ? 'all' : 'none'};`;
  }, []);

  const loop = useCallback((now: number) => {
    const springs = springsRef.current, target = targetRef.current;
    if (!springs || !target) return;
    const dt = Math.min((now - lastTimeRef.current) / 1000, 0.033);
    lastTimeRef.current = now;
    const finished = tickSprings(springs, dt, target);
    const reverseSnap = springs.direction === 'reverse' && !finished && springs.shape.v < 0.15;
    if (reverseSnap || (finished && springs.direction === 'reverse')) {
      pathRef.current?.setAttribute('d', '');
      glowRef.current?.setAttribute('d', '');
      if (menuRef.current) menuRef.current.style.opacity = '0';
      if (pillRef.current) { pillRef.current.style.opacity = '1'; pillRef.current.style.pointerEvents = 'auto'; }
      setPillHidden(false); setOverlayActive(false); springsRef.current = null;
      pillRef.current?.animate([
        { transform: 'scale(0.88)', offset: 0 }, { transform: 'scale(1.08)', offset: 0.4 },
        { transform: 'scale(0.97)', offset: 0.7 }, { transform: 'scale(1)', offset: 1 },
      ], { duration: 350, easing: 'ease-out' });
      return;
    }
    const state = readState(springs, target);
    apply(state);
    if (springs.direction === 'forward' && !menuBouncedRef.current && springs.shape.v > 0.85) {
      menuBouncedRef.current = true;
      menuRef.current?.animate([
        { transform: 'scale(0.97)', offset: 0 }, { transform: 'scale(1.02)', offset: 0.4 },
        { transform: 'scale(0.995)', offset: 0.7 }, { transform: 'scale(1)', offset: 1 },
      ], { duration: 300, easing: 'ease-out' });
    }
    if (finished) { springsRef.current = null; return; }
    rafRef.current = requestAnimationFrame(loop);
  }, [apply]);

  const getTarget = useCallback((): MorphTarget => {
    const r = pillRef.current!.getBoundingClientRect();
    return {
      pillLeft: r.left, pillRight: r.right, pillTop: r.top,
      pillCx: r.left + r.width / 2, pillCy: r.top + r.height / 2,
      pillWidth: PILL_W, pillHeight: PILL_H,
      menuWidth: MENU_W, menuHeight: MENU_H, menuRadius: MENU_R,
    };
  }, []);

  const open = useCallback(() => {
    if (springsRef.current) return;
    const target = getTarget(); targetRef.current = target;
    setPillHidden(true); setOverlayActive(true); menuBouncedRef.current = false;
    cancelAnimationFrame(rafRef.current);
    springsRef.current = createSprings(target, 'forward');
    lastTimeRef.current = performance.now();
    rafRef.current = requestAnimationFrame(loop);
  }, [getTarget, loop]);

  const close = useCallback(() => {
    if (springsRef.current?.direction === 'reverse') return;
    const target = targetRef.current ?? getTarget(); targetRef.current = target;
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
    return () => { window.removeEventListener('keydown', onKey); cancelAnimationFrame(rafRef.current); };
  }, [close]);

  const handleItemClick = useCallback((item: MenuItem) => {
    if ('action' in item && item.action && onAction) onAction(item.action);
    if ('view' in item && item.view && onNavigate) onNavigate(item.view);
    close();
  }, [close, onAction, onNavigate]);

  const overlay = (
    <div onClick={overlayActive ? onOverlayClick : undefined}
      style={{ position: 'fixed', inset: 0, zIndex: 100, pointerEvents: overlayActive ? 'all' : 'none' }}>
      <svg width="100%" height="100%" style={{ position: 'absolute', inset: 0 }}>
        <path ref={glowRef} fill="none" stroke="rgba(125,249,255,0.15)" strokeWidth="16" opacity="0" style={{ filter: 'blur(12px)' }} />
        <path ref={pathRef} fill="rgba(255,255,255,0.98)" stroke="rgba(0,0,0,0.06)" strokeWidth="0.5"
          style={{ filter: 'drop-shadow(0 4px 24px rgba(0,0,0,0.12))' }} />
      </svg>
      <div ref={menuRef} style={{ position: 'fixed', opacity: 0, overflow: 'hidden', pointerEvents: 'none', borderRadius: MENU_R }}>
        <div style={{ padding: '8px' }}>
          {NAV_ITEMS.map((item, i) => {
            if ('sep' in item) return <div key={i} style={{ height: 1, margin: '4px 12px', background: 'rgba(0,0,0,0.06)' }} />;
            const isActive = 'view' in item && item.view === activeView;
            return (
              <div key={i} onClick={() => handleItemClick(item)} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '10px 14px', cursor: 'pointer',
                color: item.danger ? '#ef4444' : item.accent ? '#0097A7' : '#1a1a2e',
                fontSize: 13, fontWeight: isActive ? 700 : 500,
                borderRadius: 10, margin: '1px 0',
                background: isActive ? 'rgba(125,249,255,0.08)' : 'transparent',
                fontFamily: "'Sora', sans-serif",
              }}
              onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'rgba(0,0,0,0.04)'; }}
              onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
              >
                <span>{item.label}</span>
                {isActive && <div style={{ width: 6, height: 6, borderRadius: 3, background: '#7DF9FF' }} />}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  return (
    <>
      <button ref={pillRef} onClick={open} style={{
        width: PILL_W, height: PILL_H, borderRadius: PILL_H / 2,
        border: '1px solid rgba(0,0,0,0.08)', background: 'rgba(0,0,0,0.03)',
        cursor: 'pointer', outline: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center',
        opacity: pillHidden ? 0 : 1, pointerEvents: pillHidden ? 'none' : 'auto',
        position: 'relative', zIndex: 20, transition: 'background 0.15s',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.06)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.03)')}
      >
        <svg width="15" height="11" viewBox="0 0 15 11" fill="none">
          <rect y="0" width="15" height="2" rx="1" fill="rgba(0,0,0,0.5)"/>
          <rect y="4.5" width="15" height="2" rx="1" fill="rgba(0,0,0,0.5)"/>
          <rect y="9" width="15" height="2" rx="1" fill="rgba(0,0,0,0.5)"/>
        </svg>
      </button>
      {createPortal(overlay, document.body)}
    </>
  );
}
