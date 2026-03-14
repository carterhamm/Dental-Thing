# CLAUDE-PM.md — Agent Runtime (Spencer)

## Project Overview

Dental rescheduling agent that autonomously fills cancelled appointment slots. When a patient cancels, the AI agent scores candidates, contacts them via voice/SMS, and keeps going until the slot is filled.

**Your role:** Build the Claude Agent SDK orchestrator. You call Eddy's brain functions to make decisions, then write outreach intents to Firestore. The UI/Voice person watches Firestore and executes the actual calls/SMS via ElevenLabs and Twilio. You never touch comms APIs directly.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Code (PM)                           │
│                   Claude Agent SDK Orchestrator                  │
│                                                                 │
│  1. Detect cancellation (Firestore watch or HTTP trigger)       │
│  2. Call brain.score_candidates() ← Eddy's code                │
│  3. Call brain.get_next_action() ← Eddy's code                 │
│  4. Write outreach intent to Firestore:                        │
│     - { type: "voice", phone, message } → UI/Voice executes    │
│       via ElevenLabs + Twilio                                   │
│     - { type: "sms", phone, message } → UI/Voice executes      │
│       via Twilio                                                │
│  5. Wait for outcome (UI/Voice writes result to Firestore)     │
│  6. Call brain.update_candidate_status()                       │
│  7. Write activity to Firestore                                │
│  8. Loop back to step 3 until done or give_up                  │
└─────────────────────────────────────────────────────────────────┘
```

**You do NOT call Twilio or ElevenLabs directly.** You write intent to Firestore, the UI/Voice person's code picks it up and executes it. Firestore is the message bus between you and the comms layer.

---

## Claude Agent SDK Setup

Install the Claude Agent SDK:

```bash
pip install claude-agent-sdk anthropic
```

### Agent Pattern with Tool Use

```python
from claude_agent_sdk import Agent, tool
from brain import score_candidates, get_next_action, update_candidate_status
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid
import time

# Firebase setup
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
session_ref = db.collection("sessions").document("current")


# Define tools the agent can use
@tool
def rank_candidates(recall_list: list[dict], slot: dict) -> list[dict]:
    """Score and rank waitlist candidates for the open slot."""
    return score_candidates(recall_list, slot)


@tool
def decide_next_action(candidates: list[dict], current_index: int) -> dict:
    """Decide the next action: call, sms, next_candidate, give_up, or done."""
    action, idx = get_next_action(candidates, current_index)
    return {"action": action, "candidate_index": idx}


@tool
def request_voice_call(phone: str, patient_name: str, message: str) -> dict:
    """Request a voice call to a patient. UI/Voice layer will execute via ElevenLabs."""
    action_id = f"action_{uuid.uuid4().hex[:8]}"
    session_ref.update({
        "pending_action": {
            "id": action_id,
            "type": "voice",
            "phone": phone,
            "patient_name": patient_name,
            "message": message,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    })
    return {"action_id": action_id, "status": "requested"}


@tool
def request_sms(phone: str, patient_name: str, message: str) -> dict:
    """Request an SMS to a patient. UI/Voice layer will execute via Twilio."""
    action_id = f"action_{uuid.uuid4().hex[:8]}"
    session_ref.update({
        "pending_action": {
            "id": action_id,
            "type": "sms",
            "phone": phone,
            "patient_name": patient_name,
            "message": message,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    })
    return {"action_id": action_id, "status": "requested"}


@tool
def check_outreach_outcome() -> dict:
    """Check if the UI/Voice layer has written an outcome for the pending action."""
    doc = session_ref.get()
    data = doc.to_dict()
    outcome = data.get("pending_outcome")
    if outcome:
        # Clear the outcome after reading
        session_ref.update({"pending_outcome": firestore.DELETE_FIELD})
        return outcome
    return {"status": "waiting"}


@tool
def book_appointment(candidate_name: str, slot: dict) -> dict:
    """Book the appointment — mark slot as filled, update status."""
    session_ref.update({
        "slot.status": "filled",
        "slot.filled_by": candidate_name,
        "agent_status": "complete",
        "recovered": slot.get("value", 0)
    })
    return {"status": "booked", "patient": candidate_name}


@tool
def update_status(candidates: list[dict], index: int, new_status: str) -> list[dict]:
    """Update a candidate's status and sync to Firestore."""
    updated = update_candidate_status(candidates, index, new_status)
    session_ref.update({"candidates": updated})
    return updated


# Build the agent
agent = Agent(
    model="claude-sonnet-4-20250514",
    tools=[rank_candidates, decide_next_action, request_voice_call,
           request_sms, check_outreach_outcome, book_appointment, update_status],
    system="""You are a dental scheduling AI agent. Your job is to fill a cancelled appointment slot by contacting waitlist candidates.

Your workflow:
1. Rank candidates using rank_candidates
2. Start with the highest-ranked candidate
3. Use decide_next_action to determine whether to call or SMS
4. Request outreach via request_voice_call or request_sms (these write to Firestore — the comms layer executes them)
5. Poll check_outreach_outcome until you get a result
6. Based on the outcome, either book_appointment (if confirmed) or update_status and move to the next candidate
7. Log your reasoning as you go — the activity feed shows your thinking to the judges

Be conversational in your activity logs. Sound like a smart assistant, not a robot.
Keep trying candidates until the slot is filled or all candidates are exhausted."""
)
```

### Running the Agent

```python
def run_agent(slot: dict, recall_list: list[dict]):
    """Trigger the agent with context about the cancellation."""

    # Set status
    set_agent_status("running")
    log_activity("event", "Cancellation detected — agent starting")

    # Run the agent with the context
    result = agent.run(
        f"""A patient just cancelled their {slot['treatment']} appointment at {slot['time']}.

Slot details: {slot}
Recall list: {recall_list}

Fill this slot. Start by ranking candidates, then work through them one by one."""
    )

    return result
```

---

## Firestore Integration

Reference Eddy's `CLAUDE-BE.md` for the full schema. Here's what you write:

### Writing Activity Logs

Every action should be logged so the UI can show it:

```python
def log_activity(activity_type: str, text: str):
    """Add activity entry. UI will see this instantly via onSnapshot."""
    session_ref.update({
        "activity": firestore.ArrayUnion([{
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "type": activity_type,
            "text": text,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }])
    })

# Usage examples:
log_activity("event", "Cancellation received — agent starting")
log_activity("thinking", "Scoring 4 candidates from recall list...")
log_activity("tool_call", "Requesting voice call to Sarah Kim...")
log_activity("call_outcome", "No answer — falling back to SMS")
log_activity("sms_sent", "SMS requested for Sarah Kim")
log_activity("success", "Slot filled by Sarah Kim. Recovered $200.")
log_activity("error", "Outreach timed out for candidate")
```

### Activity Types (Reference)

| Type | When to Log |
|------|-------------|
| `"event"` | Agent starting, cancellation detected |
| `"thinking"` | Scoring candidates, deciding next step |
| `"tool_call"` | About to request a call or SMS |
| `"call_outcome"` | Voice call finished (answered, no answer, declined) |
| `"sms_sent"` | SMS requested |
| `"success"` | Slot filled |
| `"error"` | Something went wrong |

### Updating Agent Status

```python
def set_agent_status(status: str):
    """Update agent_status. UI shows this in the top bar."""
    session_ref.update({"agent_status": status})

# Status values: "idle", "running", "complete", "failed"
```

### Updating Candidates

```python
def update_candidates_in_firestore(candidates: list[dict]):
    """Update candidate list. UI shows this in the candidate queue."""
    session_ref.update({"candidates": candidates})
```

---

## How Outreach Works (Firestore as Message Bus)

You write **intent** to Firestore. The UI/Voice person's code **executes** it.

### You Write:
```python
# Request a voice call
session_ref.update({
    "pending_action": {
        "id": "action_abc123",
        "type": "voice",          # or "sms"
        "phone": "+1-801-555-0101",
        "patient_name": "Sarah Kim",
        "message": "Hi Sarah, this is Bright Smile Dental...",
        "status": "pending",
        "created_at": "2026-03-14T10:32:00Z"
    }
})
```

### UI/Voice Person Reads + Executes:
- They watch `pending_action` via Firestore `onSnapshot`
- If `type: "voice"` → they call via ElevenLabs + Twilio
- If `type: "sms"` → they send via Twilio
- They update `pending_action.status` to `"sent"` / `"in_progress"`

### UI/Voice Person Writes Outcome:
```python
# They write this when the call/SMS completes
session_ref.update({
    "pending_outcome": {
        "type": "voice",           # or "sms"
        "result": "no_answer",     # "confirmed" | "declined" | "no_answer"
        "details": "Call rang for 30 seconds, no pickup",
        "completed_at": "2026-03-14T10:33:00Z"
    }
})
```

### You Read the Outcome:
```python
# Poll or watch for pending_outcome
doc = session_ref.get()
outcome = doc.to_dict().get("pending_outcome")
if outcome:
    # Process it, clear it
    session_ref.update({"pending_outcome": firestore.DELETE_FIELD})
```

---

## Demo Flow

For the hackathon demo:

1. **Judge clicks "Trigger Cancellation"** → UI writes `slot.status = "cancelled"` to Firestore
2. **You detect the change** → Start agent loop
3. **Agent scores candidates** → Log "thinking" activity
4. **Agent requests voice call** → Writes `pending_action` to Firestore
5. **UI/Voice executes the call** via ElevenLabs → Writes `pending_outcome`
6. **Agent reads outcome** → If no answer, requests SMS fallback
7. **If declined, try next candidate** → Repeat
8. **Slot filled** → Log "success", update status to "complete"
9. **Judge sees it all in real-time** in the activity feed

---

## Triggering the Agent

### Option A: Watch Firestore for Cancellations

```python
def on_snapshot(doc_snapshot, changes, read_time):
    for doc in doc_snapshot:
        data = doc.to_dict()
        if data["slot"]["status"] == "cancelled" and data["agent_status"] == "idle":
            run_agent(data["slot"], RECALL_LIST)

session_ref.on_snapshot(on_snapshot)
```

### Option B: HTTP Trigger (Simpler for Demo)

```python
from flask import Flask
app = Flask(__name__)

@app.route("/start-agent", methods=["POST"])
def start_agent():
    doc = session_ref.get()
    data = doc.to_dict()
    run_agent(data["slot"], RECALL_LIST)
    return {"status": "started"}
```

---

## Environment Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_APPLICATION_CREDENTIALS=path/to/serviceAccountKey.json
```

---

## Handoff Checklist

- [ ] Get `brain.py` from Eddy — test the functions work
- [ ] Get Firebase service account from UI/Voice person
- [ ] Test writing `pending_action` and reading `pending_outcome` round-trip
- [ ] Test the full loop with mock data
- [ ] Run a dry demo before judges see it

---

## Reference

- **Firestore schema:** See `CLAUDE-BE.md` (Eddy's doc) — that's the source of truth
- **UI components:** See `CLAUDE-UI.md` — understand what they're displaying
- **Claude Agent SDK docs:** https://docs.anthropic.com/en/docs/agents-and-tools/claude-agent-sdk
