import {
  collection,
  doc,
  setDoc,
  addDoc,
  updateDoc,
  deleteDoc,
  getDocs,
  onSnapshot,
  query,
  orderBy,
  serverTimestamp,
  Timestamp,
} from 'firebase/firestore';
import { db } from './firebase';

// --- Types ---

export interface SlotDoc {
  patientName: string;
  slotTime: string;
  slotDate: string;
  duration: number;
  estimatedRevenue: number;
  status: 'open' | 'booking' | 'filled';
  bookedBy?: string;
}

export interface PatientDoc {
  firstName: string;
  lastName: string;
  birthday: string;
  age: number;
  phone: string;
  email: string;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
  };
  insurance: {
    provider: string;
    planId: string;
  };
  previousAppointments: Array<{
    date: string;
    type: string;
    provider: string;
    notes?: string;
  }>;
  upcomingAppointments: Array<{
    date: string;
    time: string;
    type: string;
    provider: string;
  }>;
  lastCleaning: string;
  preferredContact: 'phone' | 'sms' | 'email';
  status: 'active' | 'inactive';
  outreachStatus: string;
  order: number;
}

export interface LogDoc {
  icon: string;
  message: string;
  type: 'call' | 'sms' | 'system' | 'success' | 'warning';
  timestamp: Timestamp;
}

export interface AgentDoc {
  phase: string;
  currentPatient: string;
  attempt: number;
  totalPatients: number;
}

// --- Mock Patient Data ---

const MOCK_PATIENTS: Omit<PatientDoc, 'order' | 'outreachStatus'>[] = [
  {
    firstName: 'Sarah', lastName: 'Chen',
    birthday: '1989-03-15', age: 36,
    phone: '(555) 012-3456', email: 'sarah.chen@email.com',
    address: { street: '142 Oak Lane', city: 'Lehi', state: 'UT', zip: '84043' },
    insurance: { provider: 'Delta Dental', planId: 'DDU-8842' },
    previousAppointments: [
      { date: '2025-07-12', type: 'Cleaning', provider: 'Dr. Martinez', notes: 'Routine cleaning, no issues' },
      { date: '2025-01-08', type: 'Cleaning', provider: 'Dr. Martinez', notes: 'Slight buildup on lower molars' },
      { date: '2024-07-20', type: 'Filling', provider: 'Dr. Wilson', notes: 'Composite filling, tooth #14' },
    ],
    upcomingAppointments: [],
    lastCleaning: '2025-07-12', preferredContact: 'phone', status: 'active',
  },
  {
    firstName: 'James', lastName: 'Patel',
    birthday: '1975-11-22', age: 50,
    phone: '(555) 234-5678', email: 'james.patel@email.com',
    address: { street: '89 Maple Dr', city: 'Provo', state: 'UT', zip: '84601' },
    insurance: { provider: 'Cigna Dental', planId: 'CIG-3391' },
    previousAppointments: [
      { date: '2025-08-20', type: 'Crown', provider: 'Dr. Wilson', notes: 'Porcelain crown, tooth #30' },
      { date: '2025-06-15', type: 'Cleaning', provider: 'Dr. Martinez' },
    ],
    upcomingAppointments: [],
    lastCleaning: '2025-06-15', preferredContact: 'sms', status: 'active',
  },
  {
    firstName: 'Maria', lastName: 'Santos',
    birthday: '1997-06-03', age: 28,
    phone: '(555) 345-6789', email: 'maria.santos@email.com',
    address: { street: '2201 Center St', city: 'American Fork', state: 'UT', zip: '84003' },
    insurance: { provider: 'Blue Cross', planId: 'BCU-7710' },
    previousAppointments: [
      { date: '2025-06-28', type: 'Cleaning', provider: 'Dr. Martinez' },
      { date: '2024-12-15', type: 'Cleaning', provider: 'Dr. Martinez' },
    ],
    upcomingAppointments: [],
    lastCleaning: '2025-06-28', preferredContact: 'phone', status: 'active',
  },
  {
    firstName: 'Tom', lastName: 'Bradley',
    birthday: '1980-09-14', age: 45,
    phone: '(555) 456-7890', email: 'tom.bradley@email.com',
    address: { street: '560 Pleasant View Dr', city: 'Pleasant Grove', state: 'UT', zip: '84062' },
    insurance: { provider: 'Aetna', planId: 'AET-5523' },
    previousAppointments: [
      { date: '2025-09-01', type: 'Root Canal', provider: 'Dr. Wilson', notes: 'Tooth #19, follow-up in 2 weeks' },
      { date: '2025-07-10', type: 'Cleaning', provider: 'Dr. Martinez' },
    ],
    upcomingAppointments: [
      { date: '2026-04-10', time: '10:00 AM', type: 'Follow-up', provider: 'Dr. Wilson' },
    ],
    lastCleaning: '2025-07-10', preferredContact: 'phone', status: 'active',
  },
  {
    firstName: 'Emma', lastName: 'Liu',
    birthday: '1993-12-07', age: 32,
    phone: '(555) 567-8901', email: 'emma.liu@email.com',
    address: { street: '1034 State St', city: 'Orem', state: 'UT', zip: '84057' },
    insurance: { provider: 'Delta Dental', planId: 'DDU-4419' },
    previousAppointments: [
      { date: '2025-07-22', type: 'Cleaning', provider: 'Dr. Martinez' },
      { date: '2025-03-05', type: 'Whitening', provider: 'Dr. Martinez' },
    ],
    upcomingAppointments: [],
    lastCleaning: '2025-07-22', preferredContact: 'sms', status: 'active',
  },
  {
    firstName: 'David', lastName: 'Kim',
    birthday: '1964-04-30', age: 61,
    phone: '(555) 678-9012', email: 'david.kim@email.com',
    address: { street: '78 Lakeview Rd', city: 'Saratoga Springs', state: 'UT', zip: '84045' },
    insurance: { provider: 'United Healthcare', planId: 'UHC-9927' },
    previousAppointments: [
      { date: '2025-10-01', type: 'Cleaning', provider: 'Dr. Martinez' },
      { date: '2025-05-18', type: 'Bridge', provider: 'Dr. Wilson', notes: '3-unit bridge, teeth #3-5' },
    ],
    upcomingAppointments: [],
    lastCleaning: '2025-10-01', preferredContact: 'phone', status: 'active',
  },
  {
    firstName: 'Lisa', lastName: 'Thompson',
    birthday: '1986-08-19', age: 39,
    phone: '(555) 789-0123', email: 'lisa.thompson@email.com',
    address: { street: '335 Eagle Mountain Blvd', city: 'Eagle Mountain', state: 'UT', zip: '84005' },
    insurance: { provider: 'MetLife', planId: 'MLF-6614' },
    previousAppointments: [
      { date: '2025-10-15', type: 'Cleaning', provider: 'Dr. Martinez' },
      { date: '2025-04-22', type: 'Cleaning', provider: 'Dr. Martinez' },
    ],
    upcomingAppointments: [],
    lastCleaning: '2025-10-15', preferredContact: 'email', status: 'active',
  },
  {
    firstName: 'Ryan', lastName: 'Garcia',
    birthday: '2000-01-25', age: 26,
    phone: '(555) 890-1234', email: 'ryan.garcia@email.com',
    address: { street: '1502 Main St', city: 'Spanish Fork', state: 'UT', zip: '84660' },
    insurance: { provider: 'Cigna Dental', planId: 'CIG-2205' },
    previousAppointments: [
      { date: '2025-11-03', type: 'Cleaning', provider: 'Dr. Martinez' },
      { date: '2025-05-10', type: 'Cleaning', provider: 'Dr. Martinez' },
    ],
    upcomingAppointments: [],
    lastCleaning: '2025-11-03', preferredContact: 'sms', status: 'active',
  },
];

// How many months ago was the last cleaning (for display)
function monthsAgo(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const months = (now.getFullYear() - d.getFullYear()) * 12 + (now.getMonth() - d.getMonth());
  return months <= 1 ? '1 month ago' : `${months} months ago`;
}

// --- Seed functions ---

export async function seedMockPatients() {
  for (let i = 0; i < MOCK_PATIENTS.length; i++) {
    const p = MOCK_PATIENTS[i];
    await setDoc(doc(db, 'patients', `p${i}`), {
      ...p,
      outreachStatus: 'queued',
      order: i,
    });
  }
}

export async function seedDemoData() {
  await setDoc(doc(db, 'slots', 'active'), {
    patientName: 'Marcus Webb',
    slotTime: '2:30 PM',
    slotDate: new Date().toISOString().split('T')[0],
    duration: 60,
    estimatedRevenue: 185,
    status: 'open',
  });

  await setDoc(doc(db, 'agent', 'status'), {
    phase: 'idle',
    currentPatient: '',
    attempt: 0,
    totalPatients: 8,
  });

  await seedMockPatients();

  // Clear old logs
  const logsSnap = await getDocs(collection(db, 'activity_log'));
  for (const d of logsSnap.docs) {
    await deleteDoc(d.ref);
  }

  await addDoc(collection(db, 'activity_log'), {
    icon: '⚠️',
    message: 'Cancellation received — Marcus Webb',
    type: 'warning',
    timestamp: serverTimestamp(),
  });
}

// --- Real-time listeners ---

export function onSlotChange(cb: (slot: SlotDoc) => void) {
  return onSnapshot(doc(db, 'slots', 'active'), (snap) => {
    if (snap.exists()) cb(snap.data() as SlotDoc);
  });
}

export function onAgentChange(cb: (agent: AgentDoc) => void) {
  return onSnapshot(doc(db, 'agent', 'status'), (snap) => {
    if (snap.exists()) cb(snap.data() as AgentDoc);
  });
}

export function onPatientsChange(cb: (patients: PatientDoc[]) => void) {
  const q = query(collection(db, 'patients'), orderBy('order'));
  return onSnapshot(q, (snap) => {
    cb(snap.docs.map(d => d.data() as PatientDoc));
  });
}

export function onLogsChange(cb: (logs: LogDoc[]) => void) {
  const q = query(collection(db, 'activity_log'), orderBy('timestamp', 'desc'));
  return onSnapshot(q, (snap) => {
    cb(snap.docs.map(d => d.data() as LogDoc));
  });
}

// --- Write helpers ---

export async function updateSlot(data: Partial<SlotDoc>) {
  await updateDoc(doc(db, 'slots', 'active'), data);
}

export async function updateAgent(data: Partial<AgentDoc>) {
  await updateDoc(doc(db, 'agent', 'status'), data);
}

export async function updatePatient(id: string, data: Partial<PatientDoc>) {
  await updateDoc(doc(db, 'patients', id), data);
}

export async function addLog(icon: string, message: string, type: LogDoc['type']) {
  await addDoc(collection(db, 'activity_log'), {
    icon,
    message,
    type,
    timestamp: serverTimestamp(),
  });
}

export { monthsAgo };
