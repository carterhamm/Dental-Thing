import { doc, setDoc, onSnapshot } from 'firebase/firestore';
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

export async function seedSessionData() {
  await setDoc(doc(db, 'sessions', 'current'), {
    slot: {
      id: 'slot_001',
      time: '2:00 PM',
      date: 'Today',
      treatment: 'cleaning',
      value: 200,
      status: 'cancelled',
      filled_by: null,
    },
    activity: [],
    candidates: [],
    recovered: 0,
    agent_status: 'idle',
  });
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
