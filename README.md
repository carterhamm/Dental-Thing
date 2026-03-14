# DentAI - Intelligent Dental Appointment Recovery

An AI-powered system that automatically fills last-minute cancellations by intelligently contacting patients from a recall list. Built with Claude AI for decision-making and ElevenLabs for voice calls.

## What It Does

When a patient cancels their dental appointment:
1. **Claude AI** analyzes the recall list and ranks patients by fit (treatment match, reliability, time preference)
2. **The agent** automatically calls the top candidate via ElevenLabs voice AI
3. **If they decline or don't answer**, the agent moves to the next candidate
4. **When someone confirms**, the slot is filled and the dashboard updates in real-time

## Tech Stack

- **Backend**: FastAPI (Python) + Claude AI (Anthropic)
- **Frontend**: React + Vite + TypeScript + Tailwind CSS
- **Database**: Firebase Firestore (real-time sync)
- **Voice**: ElevenLabs Conversational AI
- **SMS**: Twilio (fallback)

---

## Quick Start (For Judges)

### Prerequisites
- Python 3.11+
- Node.js 18+
- Firebase project with Firestore enabled
- Anthropic API key (with credits)

### 1. Clone and Install

```bash
# Clone the repo
git clone <repo-url>
cd Dental-Thing

# Backend dependencies
python -m venv venv
./venv/bin/pip install -r requirements.txt

# Frontend dependencies
npm install
```

### 2. Configure Environment

Create a `.env` file:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Firebase (download serviceAccountKey.json from Firebase Console)
GOOGLE_APPLICATION_CREDENTIALS=serviceAccountKey.json

# Optional - for live voice calls
ELEVENLABS_API_KEY=...
ELEVENLABS_AGENT_ID=...
ELEVENLABS_PHONE_NUMBER_ID=...

# Optional - for SMS fallback
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
```

### 3. Run Locally

```bash
# Terminal 1 - Backend
./venv/bin/uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
npm run dev
```

Open http://localhost:5173 to see the dashboard.

---

## Demo Flow

### Option A: Full Demo (with ElevenLabs)

1. Click **"Trigger Cancellation"** on the dashboard
2. Watch Claude rank the patients in the queue
3. The agent calls the top patient automatically
4. When they answer, the ElevenLabs voice AI handles the conversation
5. After the call, the outcome is processed and the schedule updates

### Option B: Simulated Demo (without ElevenLabs)

If ElevenLabs isn't configured, you can simulate the flow:

```bash
# 1. Reset the state
curl -X POST http://localhost:8000/reset

# 2. Trigger a cancellation (Claude will rank patients)
curl -X POST http://localhost:8000/cancellation

# 3. Simulate a patient confirming
curl -X POST http://localhost:8000/call-outcome \
  -H "Content-Type: application/json" \
  -d '{"patient_name": "Podium Judge", "outcome": "confirmed"}'
```

Watch the dashboard update in real-time as each step happens.

---

## Dashboard Components

| Component | Description |
|-----------|-------------|
| **Stats Bar** | Shows filled slots, revenue recovered, calls made, texts sent |
| **Cancellation Slot** | The slot being filled (red = open, cyan = filled) |
| **Agent Status** | Current agent phase (idle, ranking, calling, texting) |
| **Daily Schedule** | Today's appointments with live status updates |
| **Patient Queue** | Ranked list of candidates being contacted |
| **Activity Log** | Real-time feed of all agent actions |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/cancellation` | POST | Trigger the agent to fill a cancellation |
| `/reset` | POST | Reset all state to initial demo data |
| `/call-outcome` | POST | Process call result (confirmed/declined/no_answer) |
| `/sms-reply` | POST | Process SMS reply |
| `/webhooks/twilio-sms` | POST | Twilio SMS webhook |
| `/webhooks/elevenlabs` | POST | ElevenLabs post-call webhook |

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   React App     │────▶│   FastAPI        │────▶│   Claude AI     │
│   (Dashboard)   │     │   (Backend)      │     │   (Brain)       │
└────────┬────────┘     └────────┬─────────┘     └─────────────────┘
         │                       │
         │                       ▼
         │              ┌──────────────────┐
         │              │   ElevenLabs     │
         │              │   (Voice Calls)  │
         │              └──────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────────┐
│              Firebase Firestore             │
│   (Real-time sync between all components)   │
└─────────────────────────────────────────────┘
```

---

## Mock Data

The demo uses mock patient data in `agent/mock_data.py`:
- 18 patients on the recall list
- Various treatments: cleaning, filling, crown, root canal, whitening
- Realistic attributes: reliability scores, time preferences, overdue cycles

The daily schedule in `agent/mock_schedule.py`:
- 6 appointment slots
- 1 cancellation at 2:00 PM (cleaning, $200)

---

## Key Files

```
├── main.py                 # FastAPI server & endpoints
├── orchestrator.py         # Claude AI orchestration loop
├── agent/
│   ├── brain.py            # Scoring & decision logic
│   ├── firestore.py        # Database operations
│   ├── mock_data.py        # Patient recall list
│   ├── mock_schedule.py    # Daily schedule data
│   └── state.py            # State machine definitions
├── src/
│   ├── App.tsx             # Main React app
│   ├── lib/firestore.ts    # Frontend Firestore listeners
│   └── components/
│       └── dashboard/      # Dashboard UI components
└── tests/
    └── test_agent.py       # Backend unit tests
```

---

## Running Tests

```bash
./venv/bin/pytest -v
```

All 20 tests should pass.

---

## Team

Built by **DentAI** for the **Podium AI Hackathon**
