import { doc, onSnapshot } from 'firebase/firestore';
import { db } from './firebase';

// Backend uses sessions/current as the single source of truth

export interface SessionData {
  slot: {
    id: string;
    time: string;
    date: string;
    treatment: string;
    value: number;
    status: 'open' | 'cancelled' | 'filling' | 'filled' | 'exhausted';
    filled_by: string | null;
  };
  activity: Array<{
    id: string;
    type: 'event' | 'thinking' | 'tool_call' | 'call_outcome' | 'sms_sent' | 'success' | 'error';
    text: string;
    timestamp: string;
  }>;
  candidates: Array<{
    rank: number;
    name: string;
    phone: string;
    score: number;
    status: 'waiting' | 'calling' | 'texting' | 'declined' | 'no_answer' | 'no_reply' | 'confirmed';
    treatment_needed: string;
    days_overdue: number;
  }>;
  recovered: number;
  agent_status: 'idle' | 'running' | 'complete' | 'failed';
}

export function onSessionChange(cb: (data: SessionData | null) => void) {
  return onSnapshot(doc(db, 'sessions', 'current'), (snap) => {
    if (snap.exists()) {
      cb(snap.data() as SessionData);
    } else {
      cb(null);
    }
  }, () => {
    // Firestore error (not configured yet, etc.) — silent fail
    cb(null);
  });
}
