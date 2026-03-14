# CLAUDE-PM.md — Agent Runtime (PM)

## Project Overview

Dental rescheduling agent that autonomously fills cancelled appointment slots. When a patient cancels, the AI agent scores candidates, contacts them via voice/SMS, and keeps going until the slot is filled.

**Your role:** Build the Claude SDK agent that orchestrates the flow. You call Eddy's brain functions to make decisions, then trigger actions (via UI person's Bland.ai/Twilio code). You write activity logs to Firestore so the UI can display them in real-time.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Code (PM)                           │
│                     Claude SDK Agent Loop                       │
│                                                                 │
│  1. Detect cancellation (Firestore watch or trigger)           │
│  2. Call brain.score_candidates() ← Eddy's code                │
│  3. Call brain.get_next_action() ← Eddy's code                  │
│  4. Execute action:                                             │
│     - "call" → Tell UI to call via Bland.ai                    │
│     - "sms" → Tell UI to send SMS via Twilio                   │
│  5. Wait for outcome (webhook writes to Firestore)             │
│  6. Call brain.update_candidate_status()                       │
│  7. Write activity to Firestore                                │
│  8. Loop back to step 3 until done or give_up                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Claude SDK Setup

Install the Anthropic SDK:

```bash
pip install anthropic
```

### Basic Agent Pattern

```python
import anthropic
from brain import score_candidates, get_next_action, update_candidate_status

client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

def run_agent(slot: dict, recall_list: list[dict]):
    """Main agent loop."""

    # Step 1: Score candidates
    candidates = score_candidates(recall_list, slot)
    current_index = 0

    while True:
        # Step 2: Get next action from brain
        action, candidate_index = get_next_action(candidates, current_index)

        if action == "done":
            # Slot filled!
            return {"status": "complete", "filled_by": candidates[candidate_index]["name"]}

        if action == "give_up":
            # No more candidates
            return {"status": "failed"}

        if action == "call":
            # Trigger call via Bland.ai (UI person's code)
            # Write activity: "Calling {name}..."
            # Wait for webhook outcome
            pass

        if action == "sms":
            # Trigger SMS via Twilio (UI person's code)
            # Write activity: "Texting {name}..."
            # Wait for response or timeout
            pass

        if action == "next_candidate":
            current_index = candidate_index
            continue

        # Update candidate status based on outcome
        candidates = update_candidate_status(candidates, candidate_index, outcome)
```

### Using Claude for Reasoning (Optional)

If you want Claude to reason about decisions (for demo effect), you can add thinking steps:

```python
def get_agent_reasoning(candidates: list[dict], current_state: str) -> str:
    """Ask Claude to explain its reasoning (for activity feed)."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=150,
        messages=[{
            "role": "user",
            "content": f"""You are a dental scheduling AI. Given these candidates:
{candidates}

Current state: {current_state}

In 1-2 sentences, explain your reasoning for the next action. Be concise and professional.
Example: "Sarah Kim has the highest score (82) due to being 15 days overdue for a cleaning. Attempting call first."
"""
        }]
    )

    return response.content[0].text
```

---

## Firestore Integration

Reference Eddy's `CLAUDE-BE.md` for the full schema. Here's what you need to write:

### Writing Activity Logs

Every action should be logged so the UI can show it:

```python
from firebase_admin import firestore
from datetime import datetime
import uuid

db = firestore.client()
session_ref = db.collection("sessions").document("current")

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
log_activity("tool_call", "Calling Sarah Kim (+1-801-555-0101)...")
log_activity("call_outcome", "No answer — falling back to SMS")
log_activity("sms_sent", "SMS sent to Sarah Kim")
log_activity("success", "Slot filled by Sarah Kim. Recovered $200.")
log_activity("error", "Failed to reach Bland.ai API")
```

### Activity Types (Reference)

| Type | When to Log |
|------|-------------|
| `"event"` | Agent starting, cancellation detected |
| `"thinking"` | Scoring candidates, deciding next step |
| `"tool_call"` | About to call or text someone |
| `"call_outcome"` | Call finished (answered, no answer, declined) |
| `"sms_sent"` | SMS sent successfully |
| `"success"` | Slot filled |
| `"error"` | Something went wrong |

### Updating Agent Status

```python
def set_agent_status(status: str):
    """Update agent_status. UI shows this in the top bar."""
    session_ref.update({"agent_status": status})

# Status values: "idle", "running", "complete", "failed"
set_agent_status("running")  # When starting
set_agent_status("complete")  # When slot filled
set_agent_status("failed")  # When exhausted
```

### Updating Candidates

```python
def update_candidates_in_firestore(candidates: list[dict]):
    """Update candidate list. UI shows this in the candidate queue."""
    session_ref.update({"candidates": candidates})
```

---

## Coordination with UI Person

The UI person owns Bland.ai and Twilio API calls. You need to coordinate:

### Option A: You Call Their Functions

```python
# UI person provides these functions
from voice_api import trigger_call, send_sms

# You call them
result = trigger_call(phone="+1-801-555-0101", message="Hi, this is Bright Smile Dental...")
result = send_sms(phone="+1-801-555-0101", message="We have an opening today at 2 PM...")
```

### Option B: You Write to Firestore, They Watch

```python
# You write a "pending action" to Firestore
session_ref.update({
    "pending_action": {
        "type": "call",
        "phone": "+1-801-555-0101",
        "candidate_name": "Sarah Kim"
    }
})

# UI person's code watches for pending_action and executes it
# They write the outcome back to Firestore
# You watch for the outcome
```

**Decide with UI person which pattern to use.**

---

## Demo Flow

For the hackathon demo, the flow is:

1. **Judge clicks "Trigger Cancellation"** → UI writes `slot.status = "cancelled"` to Firestore
2. **You detect the change** → Start agent loop
3. **Agent scores candidates** → Log "thinking" activity
4. **Agent calls first candidate** → Log "tool_call" activity
5. **Call outcome arrives** (webhook) → Log "call_outcome" activity
6. **If no answer, try SMS** → Log "sms_sent" activity
7. **If declined, try next candidate** → Repeat
8. **Slot filled** → Log "success", update status to "complete"
9. **Judge sees it all in real-time** in the activity feed

---

## Triggering the Agent

Two options:

### Option A: Watch Firestore for Cancellations

```python
def on_snapshot(doc_snapshot, changes, read_time):
    for doc in doc_snapshot:
        data = doc.to_dict()
        if data["slot"]["status"] == "cancelled" and data["agent_status"] == "idle":
            # Start the agent
            run_agent(data["slot"], RECALL_LIST)

# Set up the listener
session_ref.on_snapshot(on_snapshot)
```

### Option B: HTTP Trigger (Simpler for Demo)

Run a simple Flask server that UI can call:

```python
from flask import Flask
app = Flask(__name__)

@app.route("/start-agent", methods=["POST"])
def start_agent():
    # Read current slot from Firestore
    # Run agent
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
- [ ] Get Firebase service account from UI person
- [ ] Coordinate with UI person on Bland.ai/Twilio integration pattern
- [ ] Test the full loop with mock data
- [ ] Run a dry demo before judges see it

---

## Reference

- **Firestore schema:** See `CLAUDE-BE.md` (Eddy's doc) — that's the source of truth
- **UI components:** See `CLAUDE-UI.md` — understand what they're displaying
- **Claude SDK docs:** https://docs.anthropic.com/en/docs/claude-sdk
