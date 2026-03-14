# CLAUDE-UI.md — Frontend + Comms Execution (UI/Voice Person)

## Project Overview

Dental rescheduling agent that autonomously fills cancelled appointment slots. When a patient cancels, the AI agent scores candidates, contacts them via voice/SMS, and keeps going until the slot is filled.

**Your role:** Build the React dashboard that displays everything in real-time, set up the Firebase project, and execute all outbound communications. You own ElevenLabs (voice calls) and Twilio (SMS). The PM agent writes outreach intents to Firestore — you watch for them and execute.

---

## Your Responsibilities

1. **Firebase Setup** — Create project, configure Firestore, share credentials with team
2. **React Dashboard** — Real-time UI showing schedule, agent activity, candidate queue
3. **ElevenLabs Integration** — Execute voice calls when PM agent requests them
4. **Twilio Integration** — Execute SMS when PM agent requests them, handle inbound SMS webhooks
5. **Vercel Deployment** — Deploy frontend + webhook API routes

---

## Tech Stack

- **Frontend:** React + Vite + Tailwind CSS
- **Database:** Firebase Firestore
- **Voice:** ElevenLabs Conversational AI + Twilio (phone infrastructure)
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
3. Share with Eddy and Spencer (they need it for `firebase-admin`)

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

# For Python backend (Spencer and Eddy need the JSON file path)
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
  "pending_action": null,
  "pending_outcome": null,
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
    pending_action: null,
    pending_outcome: null,
    recovered: 0,
    agent_status: "idle"
  });
}
```

---

## Comms Execution Layer (Firestore → Outbound)

**This is the key integration.** The PM agent writes `pending_action` to Firestore. You watch for it and execute.

### Watching for Outreach Requests

```javascript
import { doc, onSnapshot, updateDoc } from "firebase/firestore";
import { db } from "../firebase";

// Watch for pending actions from the PM agent
const sessionRef = doc(db, "sessions", "current");

onSnapshot(sessionRef, (snapshot) => {
  const data = snapshot.data();
  const action = data?.pending_action;

  if (action && action.status === "pending") {
    // Mark as in progress
    updateDoc(sessionRef, { "pending_action.status": "in_progress" });

    if (action.type === "voice") {
      executeVoiceCall(action);
    } else if (action.type === "sms") {
      executeSMS(action);
    }
  }
});
```

---

## ElevenLabs Integration (Voice Calls)

You own voice call execution. When the PM agent writes a `pending_action` with `type: "voice"`, you execute it.

### Setting Up ElevenLabs Conversational AI

```javascript
// ElevenLabs Conversational AI agent setup
// Create an agent in the ElevenLabs dashboard first, then use the API

async function executeVoiceCall(action) {
  const sessionRef = doc(db, "sessions", "current");

  try {
    // Step 1: Initiate call via ElevenLabs Conversational AI API
    const response = await fetch("https://api.elevenlabs.io/v1/convai/conversations", {
      method: "POST",
      headers: {
        "xi-api-key": process.env.ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        agent_id: process.env.ELEVENLABS_AGENT_ID,
        // ElevenLabs handles the Twilio phone connection
        conversation_config_override: {
          agent: {
            prompt: {
              prompt: `You are calling ${action.patient_name} from Bright Smile Dental. ${action.message}. Be warm, professional, and concise. If they say yes, confirm the time. If they say no, thank them politely.`
            },
            first_message: `Hi ${action.patient_name}, this is an assistant calling from Bright Smile Dental. We had a cancellation and have an opening today at 2 PM for a cleaning. Would you be able to come in?`
          }
        }
      })
    });

    const callData = await response.json();

    // Step 2: Update Firestore with call status
    await updateDoc(sessionRef, {
      "pending_action.status": "in_progress",
      "pending_action.call_id": callData.conversation_id
    });

    // Step 3: Outcome comes via ElevenLabs webhook (see below)

  } catch (error) {
    console.error("ElevenLabs call failed:", error);
    await updateDoc(sessionRef, {
      "pending_outcome": {
        type: "voice",
        result: "no_answer",
        details: `Call failed: ${error.message}`,
        completed_at: new Date().toISOString()
      }
    });
  }
}
```

### ElevenLabs Webhook Handler (Vercel API Route)

```javascript
// api/webhooks/elevenlabs/route.js (Next.js) or api/elevenlabs-webhook.js (Vercel serverless)

import { doc, updateDoc } from "firebase/firestore";
import { db } from "../../lib/firebase-admin";

export default async function handler(req, res) {
  const { conversation_id, status, analysis } = req.body;

  // Parse the outcome from ElevenLabs conversation analysis
  let result = "no_answer";
  if (status === "completed" && analysis) {
    // ElevenLabs provides conversation analysis/summary
    const transcript = analysis.transcript || "";
    if (analysis.call_successful || transcript.toLowerCase().includes("yes")) {
      result = "confirmed";
    } else {
      result = "declined";
    }
  }

  // Write outcome to Firestore — PM agent will pick this up
  const sessionRef = doc(db, "sessions", "current");
  await updateDoc(sessionRef, {
    "pending_outcome": {
      type: "voice",
      result: result,
      details: analysis?.summary || `Call ${status}`,
      completed_at: new Date().toISOString()
    }
  });

  res.status(200).json({ received: true });
}
```

---

## Twilio Integration (SMS)

You own SMS execution. When the PM agent writes a `pending_action` with `type: "sms"`, you send it.

### Sending SMS

```javascript
import twilio from "twilio";

const twilioClient = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);

async function executeSMS(action) {
  const sessionRef = doc(db, "sessions", "current");

  try {
    const message = await twilioClient.messages.create({
      body: action.message,
      from: process.env.TWILIO_PHONE_NUMBER,
      to: action.phone
    });

    // Mark action as sent
    await updateDoc(sessionRef, {
      "pending_action.status": "sent",
      "pending_action.twilio_sid": message.sid
    });

    // Outcome will come via Twilio inbound SMS webhook

  } catch (error) {
    console.error("Twilio SMS failed:", error);
    await updateDoc(sessionRef, {
      "pending_outcome": {
        type: "sms",
        result: "no_answer",
        details: `SMS failed: ${error.message}`,
        completed_at: new Date().toISOString()
      }
    });
  }
}
```

### Handling Inbound SMS (Twilio Webhook → Vercel API Route)

```javascript
// api/webhooks/twilio-sms/route.js

import { doc, updateDoc } from "firebase/firestore";
import { db } from "../../lib/firebase-admin";

export default async function handler(req, res) {
  const { Body, From } = req.body;

  const reply = Body.trim().toUpperCase();
  let result = "declined";

  if (["YES", "Y", "YEAH", "YEP", "SURE", "OK", "OKAY"].includes(reply)) {
    result = "confirmed";
  }

  // Write outcome to Firestore — PM agent will pick this up
  const sessionRef = doc(db, "sessions", "current");
  await updateDoc(sessionRef, {
    "pending_outcome": {
      type: "sms",
      result: result,
      details: `Patient replied: "${Body}"`,
      phone: From,
      completed_at: new Date().toISOString()
    }
  });

  // Respond to Twilio (required)
  res.setHeader("Content-Type", "text/xml");
  res.status(200).send("<Response></Response>");
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

## Vercel Deployment

### Project Structure

```
dental-dashboard/
├── src/
│   ├── App.tsx
│   ├── firebase.js
│   ├── hooks/
│   │   └── useSession.js
│   └── components/
│       ├── TopBar.tsx
│       ├── AppointmentList.tsx
│       ├── ActivityFeed.tsx
│       ├── CandidateQueue.tsx
│       └── RecoveredRevenue.tsx
├── api/
│   └── webhooks/
│       ├── elevenlabs.js          ← ElevenLabs call outcome webhook
│       └── twilio-sms.js          ← Twilio inbound SMS webhook
├── package.json
└── vercel.json
```

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
ELEVENLABS_API_KEY=...
ELEVENLABS_AGENT_ID=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
```

---

## Coordination with Team

### From Eddy (Backend Logic)
- Firestore schema (reference `CLAUDE-BE.md`)
- Activity type definitions

### From Spencer (PM / Agent Runtime)
- Writes `pending_action` to Firestore — you watch and execute
- Reads `pending_outcome` from Firestore — you write after call/SMS completes

### You Provide to Both
- Firebase credentials (service account JSON + web config)
- Webhook URLs for ElevenLabs and Twilio (once deployed on Vercel)

---

## Handoff Checklist

- [ ] Create Firebase project
- [ ] Share service account JSON with Eddy and Spencer
- [ ] Share web config / env vars
- [ ] Set up Firestore with initial demo data
- [ ] Build React components
- [ ] Integrate ElevenLabs Conversational AI
- [ ] Integrate Twilio SMS
- [ ] Deploy to Vercel
- [ ] Share webhook URLs with team
- [ ] Test full demo flow with team
