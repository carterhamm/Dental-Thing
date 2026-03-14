# CLAUDE-UI.md — Frontend + Voice APIs (UI/Voice Person)

## Project Overview

Dental rescheduling agent that autonomously fills cancelled appointment slots. When a patient cancels, the AI agent scores candidates, contacts them via voice/SMS, and keeps going until the slot is filled.

**Your role:** Build the React dashboard that displays everything in real-time, set up the Firebase project, and integrate Bland.ai (voice calls) and Twilio (SMS) APIs.

---

## Your Responsibilities

1. **Firebase Setup** — Create project, configure Firestore, share credentials with team
2. **React Dashboard** — Real-time UI showing schedule, agent activity, candidate queue
3. **Bland.ai Integration** — Trigger voice calls, handle webhooks
4. **Twilio Integration** — Send SMS messages
5. **Vercel Deployment** — Deploy frontend (coordinate with PM on any backend deployment)

---

## Tech Stack

- **Frontend:** React + Vite + Tailwind CSS
- **Database:** Firebase Firestore
- **Voice:** Bland.ai
- **SMS:** Twilio
- **Deployment:** Vercel

---

## Firebase Setup Checklist

You own Firebase setup. Others depend on you for credentials.

### Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create new project: "dental-rescheduler" (or similar)
3. Enable Firestore Database (start in test mode for hackathon)

### Step 2: Get Web Config (for React app)

1. Project Settings → General → Your apps → Add web app
2. Copy the config object:

```javascript
const firebaseConfig = {
  apiKey: "...",
  authDomain: "...",
  projectId: "...",
  storageBucket: "...",
  messagingSenderId: "...",
  appId: "..."
};
```

### Step 3: Get Service Account (for Python backend)

1. Project Settings → Service Accounts → Generate new private key
2. Download JSON file
3. Share with Eddy and PM (they need it for `firebase-admin`)

### Step 4: Share Environment Variables

Share these with the team:

```bash
# For React app (Vercel env vars)
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...

# For Python backend (PM and Eddy need the JSON file path)
GOOGLE_APPLICATION_CREDENTIALS=path/to/serviceAccountKey.json
```

### Step 5: Initialize Firestore with Demo Data

Create `sessions/current` document with initial state:

```json
{
  "slot": {
    "id": "slot_001",
    "time": "2:00 PM",
    "date": "Today",
    "treatment": "cleaning",
    "value": 200,
    "status": "open",
    "filled_by": null
  },
  "activity": [],
  "candidates": [],
  "recovered": 0,
  "agent_status": "idle"
}
```

---

## Firestore Schema (Reference)

**Source of truth is `CLAUDE-BE.md`** — Eddy owns the schema. Key points:

### `slot.status` Values

| Value | UI Display |
|-------|------------|
| `"open"` | Normal slot |
| `"cancelled"` | Red highlight, "CANCELLED" badge |
| `"filling"` | Yellow pulse, "FILLING..." badge |
| `"filled"` | Green highlight, "FILLED" badge |
| `"exhausted"` | Grey, "NO CANDIDATES" badge |

### `agent_status` Values

| Value | Top Bar Display |
|-------|-----------------|
| `"idle"` | Grey dot, "Agent standing by" |
| `"running"` | Green pulsing dot, "Agent running" |
| `"complete"` | Green checkmark, "Slot filled" |
| `"failed"` | Red dot, "Could not fill slot" |

### `activity[].type` Values

| Type | Dot Color | Text Style |
|------|-----------|------------|
| `"event"` | Grey | Normal |
| `"thinking"` | Purple | Italic |
| `"tool_call"` | Blue | Normal |
| `"call_outcome"` | Orange | Normal |
| `"sms_sent"` | Teal | Normal |
| `"success"` | Green | Bold |
| `"error"` | Red | Normal |

---

## Component Structure

```
App
├── TopBar
│   ├── Practice name ("Bright Smile Dental")
│   ├── Agent status indicator
│   ├── "Trigger Cancellation" button
│   └── "Reset Demo" button
│
├── LeftPanel (40% width)
│   ├── Today's date header
│   ├── AppointmentList
│   │   └── AppointmentSlot (×6)
│   └── RecoveredRevenue counter
│
└── RightPanel (60% width)
    ├── "Agent Activity" header
    ├── ActivityFeed (scrollable)
    │   └── ActivityItem (per log entry)
    └── CandidateQueue
        └── CandidateCard (per candidate)
```

---

## React + Firebase Setup

### Install Dependencies

```bash
npm create vite@latest dental-dashboard -- --template react
cd dental-dashboard
npm install firebase tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### Firebase Config (`src/firebase.js`)

```javascript
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
```

### Real-Time Listener (`src/hooks/useSession.js`)

```javascript
import { useEffect, useState } from "react";
import { doc, onSnapshot } from "firebase/firestore";
import { db } from "../firebase";

export function useSession() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onSnapshot(
      doc(db, "sessions", "current"),
      (snapshot) => {
        setSession(snapshot.data());
        setLoading(false);
      },
      (error) => {
        console.error("Firestore error:", error);
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, []);

  return { session, loading };
}
```

### Trigger Cancellation

```javascript
import { doc, updateDoc } from "firebase/firestore";
import { db } from "../firebase";

async function triggerCancellation() {
  const sessionRef = doc(db, "sessions", "current");
  await updateDoc(sessionRef, {
    "slot.status": "cancelled",
    "agent_status": "idle",
    "activity": [],
    "candidates": [],
    "recovered": 0
  });
}
```

### Reset Demo

```javascript
async function resetDemo() {
  const sessionRef = doc(db, "sessions", "current");
  await updateDoc(sessionRef, {
    slot: {
      id: "slot_001",
      time: "2:00 PM",
      date: "Today",
      treatment: "cleaning",
      value: 200,
      status: "open",
      filled_by: null
    },
    activity: [],
    candidates: [],
    recovered: 0,
    agent_status: "idle"
  });
}
```

---

## Mock Schedule Data

Hardcode this in the frontend. Only the 2:00 PM slot is live:

```javascript
const mockSchedule = [
  { time: "9:00 AM",  patient: "Tom Bradley",   treatment: "Crown prep",   status: "completed" },
  { time: "10:00 AM", patient: "Lisa Chen",     treatment: "Cleaning",     status: "completed" },
  { time: "11:30 AM", patient: "David Nguyen",  treatment: "X-Ray + Exam", status: "in-progress" },
  { time: "2:00 PM",  patient: null,            treatment: "Cleaning",     status: "open" }, // ← Live slot
  { time: "3:30 PM",  patient: "Emma Wilson",   treatment: "Whitening",    status: "scheduled" },
  { time: "5:00 PM",  patient: "Carlos Reyes",  treatment: "Filling",      status: "scheduled" },
];
```

The 2:00 PM slot's status comes from Firestore `slot.status`, not this array.

---

## Design Tokens

### Colors

```javascript
const colors = {
  cancelled: "#EF4444",   // Red
  filling: "#F59E0B",     // Yellow/Amber
  filled: "#10B981",      // Green
  thinking: "#7C3AED",    // Purple
  toolCall: "#3B82F6",    // Blue
  neutral: "#6B7280",     // Grey
  smsSent: "#14B8A6",     // Teal
  callOutcome: "#F97316", // Orange
  error: "#EF4444",       // Red
};
```

### Tailwind Classes

```javascript
// Activity dot colors
const activityDotClass = {
  event: "bg-gray-400",
  thinking: "bg-purple-500",
  tool_call: "bg-blue-500",
  call_outcome: "bg-orange-500",
  sms_sent: "bg-teal-500",
  success: "bg-green-500",
  error: "bg-red-500",
};

// Activity text styles
const activityTextClass = {
  thinking: "italic text-gray-600",
  success: "font-bold text-green-700",
  error: "text-red-600",
};
```

### Layout

- Two-column: Left 40%, Right 60%
- White background, clean clinical look
- System font stack

---

## Bland.ai Integration

You own voice call integration.

### Triggering a Call

```javascript
// Bland.ai API call
async function triggerCall(phone, patientName) {
  const response = await fetch("https://api.bland.ai/v1/calls", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${process.env.BLAND_API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      phone_number: phone,
      task: `You are calling ${patientName} from Bright Smile Dental. We had a cancellation and have an opening today at 2 PM for a cleaning. Ask if they would like to take this appointment.`,
      voice: "maya",
      webhook: "https://your-webhook-url.com/bland-webhook"
    })
  });

  return response.json();
}
```

### Handling Webhook

When call completes, Bland.ai sends webhook. Write outcome to Firestore:

```javascript
// Webhook handler (could be Vercel serverless function)
export default async function handler(req, res) {
  const { status, transcripts } = req.body;

  // Parse outcome from call
  let outcome = "no_answer";
  if (status === "completed") {
    // Check transcripts for yes/no
    outcome = transcripts.includes("yes") ? "confirmed" : "declined";
  }

  // Write to Firestore
  // This will trigger PM's agent to continue
  await updateDoc(doc(db, "sessions", "current"), {
    "pending_outcome": {
      type: "call",
      result: outcome
    }
  });

  res.status(200).json({ received: true });
}
```

---

## Twilio Integration

You own SMS integration.

### Sending SMS

```javascript
// Twilio API (use their Node SDK or REST API)
import twilio from "twilio";

const client = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);

async function sendSMS(phone, patientName) {
  const message = await client.messages.create({
    body: `Hi ${patientName}, this is Bright Smile Dental. We have an opening today at 2 PM for a cleaning. Reply YES to book or NO to decline.`,
    from: process.env.TWILIO_PHONE_NUMBER,
    to: phone
  });

  return message.sid;
}
```

### Handling SMS Reply (Webhook)

```javascript
// Twilio webhook handler
export default async function handler(req, res) {
  const { Body, From } = req.body;

  const reply = Body.trim().toUpperCase();
  const outcome = reply === "YES" ? "confirmed" : "declined";

  // Write to Firestore
  await updateDoc(doc(db, "sessions", "current"), {
    "pending_outcome": {
      type: "sms",
      result: outcome,
      phone: From
    }
  });

  res.status(200).send("<Response></Response>");
}
```

---

## Vercel Deployment

### Build & Deploy

```bash
npm run build
vercel --prod
```

### Environment Variables (Vercel Dashboard)

```
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
BLAND_API_KEY=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
```

---

## Animations

### Filling Slot Pulse

```css
@keyframes pulse-yellow {
  0%, 100% { background-color: #FEF3C7; }
  50% { background-color: #FDE68A; }
}

.filling-slot {
  animation: pulse-yellow 2s ease-in-out infinite;
}
```

### Activity Item Slide-In

```css
@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.activity-item {
  animation: slide-in 0.3s ease-out;
}
```

### Revenue Counter

Use a number animation library or CSS counter for the "recovered revenue" incrementing effect.

---

## Loading & Empty States

- **Loading:** Spinner with "Connecting to agent..."
- **Empty activity:** "Waiting for cancellation..."
- **Idle agent:** Subtle "Agent standing by" in top bar
- **Running agent:** Green pulsing dot + "Agent running"

Never show broken or empty UI to judges.

---

## Coordination with Team

### From Eddy (Backend Logic)
- Firestore schema (reference `CLAUDE-BE.md`)
- Activity type definitions

### From PM (Agent Runtime)
- How they want to trigger calls (you provide function, or they write to Firestore?)
- When to expect activity writes

### You Provide to Both
- Firebase credentials (service account JSON + web config)
- Webhook URLs for Bland.ai and Twilio

---

## Handoff Checklist

- [ ] Create Firebase project
- [ ] Share service account JSON with Eddy and PM
- [ ] Share web config / env vars
- [ ] Set up Firestore with initial demo data
- [ ] Build React components
- [ ] Integrate Bland.ai
- [ ] Integrate Twilio
- [ ] Deploy to Vercel
- [ ] Test full demo flow with team
