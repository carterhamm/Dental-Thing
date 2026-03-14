import { doc, collection, setDoc, onSnapshot, query, orderBy } from 'firebase/firestore';
import { db } from './firebase';

/*
  Eddy's backend writes to:
  - slots/active         → slot info
  - agent/status         → { status, recovered }
  - patients/p0, p1, ... → individual candidate docs
  - activity_log/        → activity entries with serverTimestamp
*/

// --- Types ---

export interface SlotData {
  id?: string;
  time: string;
  date: string;
  treatment: string;
  value: number;
  status: string;
  filled_by?: string | null;
}

export interface AgentData {
  status: string;
  recovered?: number;
}

export interface CandidateData {
  rank: number;
  name: string;
  phone: string;
  score: number;
  status: string;
  treatment_needed: string;
  cycles_overdue: number;
}

export interface ActivityData {
  id?: string;
  type: string;
  text: string;
  timestamp: any;
}

export interface ScheduleSlot {
  id: string;
  time: string;
  treatment: string;
  status: 'booked' | 'cancelled' | 'filled';
  patient_name: string | null;
  value: number;
}

export interface ScheduleData {
  slots: ScheduleSlot[];
}

// --- Seed / Initialize ---

export async function seedSessionData() {
  await setDoc(doc(db, 'slots', 'active'), {
    id: 'slot_001',
    time: '2:00 PM',
    date: 'Today',
    treatment: 'cleaning',
    value: 200,
    status: 'open',
    filled_by: null,
  });
  await setDoc(doc(db, 'agent', 'status'), {
    status: 'idle',
    recovered: 0,
  });
}

// --- Listeners ---

export function onSlotChange(cb: (data: SlotData | null) => void) {
  return onSnapshot(doc(db, 'slots', 'active'), (snap) => {
    cb(snap.exists() ? (snap.data() as SlotData) : null);
  }, () => cb(null));
}

export function onAgentChange(cb: (data: AgentData | null) => void) {
  return onSnapshot(doc(db, 'agent', 'status'), (snap) => {
    cb(snap.exists() ? (snap.data() as AgentData) : null);
  }, () => cb(null));
}

export function onCandidatesChange(cb: (candidates: CandidateData[]) => void) {
  const q = query(collection(db, 'patients'));
  return onSnapshot(q, (snap) => {
    const candidates = snap.docs
      .map(d => d.data() as CandidateData)
      .sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99));
    cb(candidates);
  }, () => cb([]));
}

export function onActivityChange(cb: (entries: ActivityData[]) => void) {
  const q = query(collection(db, 'activity_log'), orderBy('timestamp', 'desc'));
  return onSnapshot(q, (snap) => {
    cb(snap.docs.map(d => d.data() as ActivityData));
  }, () => cb([]));
}

export function onScheduleChange(cb: (data: ScheduleData | null) => void) {
  return onSnapshot(doc(db, 'schedule', 'today'), (snap) => {
    cb(snap.exists() ? (snap.data() as ScheduleData) : null);
  }, () => cb(null));
}

export interface CallStatusData {
  status: string;  // "idle", "ringing", "in-progress", "completed", "no-answer", "failed"
  patient_name: string;
  call_sid: string;
}

export function onCallStatusChange(cb: (data: CallStatusData | null) => void) {
  return onSnapshot(doc(db, 'call', 'active'), (snap) => {
    cb(snap.exists() ? (snap.data() as CallStatusData) : null);
  }, () => cb(null));
}
