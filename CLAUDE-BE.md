# CLAUDE-BE.md — Backend Logic (Eddy)

## Project Overview

Dental rescheduling agent that autonomously fills cancelled appointment slots. When a patient cancels, the AI agent scores candidates, contacts them via voice/SMS, and keeps going until the slot is filled.

**Your role:** Own the scoring logic, decision rules, state transitions, and Firestore schema design. You are the "brain" — PM's Claude Agent SDK orchestrator will call your functions to decide what to do.

---

## Firestore Schema (SOURCE OF TRUTH)

You own this schema. PM and UI reference it. If it changes, it changes here first.

### Collection: `sessions` → Document: `current`

```json
{
  "slot": {
    "id": "slot_001",
    "time": "2:00 PM",
    "date": "Today",
    "treatment": "cleaning",
    "value": 200,
    "status": "cancelled",
    "filled_by": null
  },
  "activity": [
    {
      "id": "act_001",
      "type": "event",
      "text": "Cancellation received — agent starting",
      "timestamp": "2024-03-14T10:00:00Z"
    }
  ],
  "candidates": [
    {
      "rank": 1,
      "name": "Sarah Kim",
      "phone": "+1-801-555-0101",
      "score": 82,
      "status": "calling",
      "treatment_needed": "cleaning",
      "days_overdue": 15
    }
  ],
  "pending_action": null,
  "pending_outcome": null,
  "recovered": 0,
  "agent_status": "idle"
}
```

### `pending_action` (PM writes, UI/Voice reads + executes)

```json
{
  "id": "action_abc123",
  "type": "voice",
  "phone": "+1-801-555-0101",
  "patient_name": "Sarah Kim",
  "message": "Hi Sarah, this is Bright Smile Dental...",
  "status": "pending",
  "created_at": "2026-03-14T10:32:00Z"
}
```

- `type`: `"voice"` (ElevenLabs + Twilio) or `"sms"` (Twilio)
- `status`: `"pending"` → `"sent"` → `"in_progress"` → `"completed"`

### `pending_outcome` (UI/Voice writes, PM reads)

```json
{
  "type": "voice",
  "result": "no_answer",
  "details": "Call rang for 30 seconds, no pickup",
  "completed_at": "2026-03-14T10:33:00Z"
}
```

- `result`: `"confirmed"` | `"declined"` | `"no_answer"`

### `slot.status` Values

| Value | Meaning |
|-------|---------|
| `"open"` | Normal scheduled slot |
| `"cancelled"` | Patient cancelled, agent not yet started |
| `"filling"` | Agent is actively working to fill |
| `"filled"` | Slot has been filled |
| `"exhausted"` | Agent tried all candidates, nobody available |

### `agent_status` Values

| Value | Meaning |
|-------|---------|
| `"idle"` | Waiting for a cancellation |
| `"running"` | Actively filling a slot |
| `"complete"` | Slot filled successfully |
| `"failed"` | Could not fill slot (exhausted candidates) |

### `activity[].type` Values

| Type | When to Use | UI Display |
|------|-------------|------------|
| `"event"` | System events (cancellation received, agent started) | Grey dot |
| `"thinking"` | Agent reasoning (scoring candidates, deciding next step) | Purple dot, italic |
| `"tool_call"` | Agent taking action (requesting call/SMS) | Blue dot |
| `"call_outcome"` | Result of a voice call (answered, no answer, declined) | Orange dot |
| `"sms_sent"` | SMS was sent | Teal dot |
| `"success"` | Slot filled, revenue logged | Green dot, bold |
| `"error"` | Something went wrong | Red dot |

### `candidates[].status` Values

| Value | Meaning |
|-------|---------|
| `"waiting"` | Not yet contacted |
| `"calling"` | Currently being called |
| `"texting"` | SMS sent, waiting for reply |
| `"declined"` | Said no |
| `"no_answer"` | Didn't pick up, no SMS reply |
| `"confirmed"` | Said yes — slot filled |

---

## Your Module: `brain.py`

PM's Claude Agent SDK orchestrator will import and call these functions. Define these interfaces clearly.

### Function Signatures

```python
from typing import Literal

# Types
CandidateStatus = Literal["waiting", "calling", "texting", "declined", "no_answer", "confirmed"]
Action = Literal["call", "sms", "next_candidate", "give_up", "done"]

def score_candidates(recall_list: list[dict], slot: dict) -> list[dict]:
    """
    Score and rank candidates for a given slot.

    Args:
        recall_list: List of patients from recall list
            [{"name": str, "phone": str, "treatment_needed": str, "days_overdue": int, "reliability_score": float}, ...]
        slot: The slot to fill
            {"treatment": str, "time": str, "date": str, "value": int}

    Returns:
        Ranked list of candidates with scores
        [{"rank": int, "name": str, "phone": str, "score": int, "status": "waiting", "treatment_needed": str, "days_overdue": int}, ...]

    Scoring factors:
        - Days overdue (more overdue = higher priority)
        - Treatment match (matches slot treatment = bonus)
        - Reliability history (higher = bonus)
    """
    pass


def get_next_action(candidates: list[dict], current_candidate_index: int) -> tuple[Action, int]:
    """
    Decide the next action based on current state.

    Args:
        candidates: Current ranked candidate list with statuses
        current_candidate_index: Index of candidate we're working on (-1 if none)

    Returns:
        (action, candidate_index)
        - ("call", 0) → Call candidate at index 0
        - ("sms", 0) → Send SMS to candidate at index 0 (fallback after no answer)
        - ("next_candidate", 1) → Move to candidate at index 1
        - ("give_up", -1) → No more candidates, mark as exhausted
        - ("done", 0) → Candidate confirmed, slot filled

    Logic:
        - If current candidate status is "waiting" → call them
        - If current candidate status is "no_answer" → try SMS
        - If current candidate status is "declined" or SMS failed → next candidate
        - If all candidates exhausted → give up
        - If any candidate is "confirmed" → done
    """
    pass


def update_candidate_status(candidates: list[dict], candidate_index: int, new_status: CandidateStatus) -> list[dict]:
    """
    Update a candidate's status and return the new list.

    Args:
        candidates: Current candidate list
        candidate_index: Which candidate to update
        new_status: New status value

    Returns:
        Updated candidate list
    """
    pass


def calculate_recovered_revenue(slot: dict) -> int:
    """
    Calculate recovered revenue when slot is filled.

    Args:
        slot: The filled slot

    Returns:
        Dollar amount recovered (slot value)
    """
    return slot.get("value", 0)
```

---

## State Transitions

### Agent Status Flow

```
idle → running (when cancellation detected)
running → complete (when slot filled)
running → failed (when all candidates exhausted)
complete → idle (when demo reset)
failed → idle (when demo reset)
```

### Slot Status Flow

```
open → cancelled (when patient cancels)
cancelled → filling (when agent starts)
filling → filled (when candidate confirms)
filling → exhausted (when no candidates left)
filled → open (when demo reset)
exhausted → open (when demo reset)
```

---

## Firestore Write Patterns

Use `firebase-admin` SDK. UI/Voice person will set up the Firebase project and share credentials.

```python
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import uuid

# Initialize (do once)
cred = credentials.Certificate("path/to/serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Reference to the session document
session_ref = db.collection("sessions").document("current")


def add_activity(activity_type: str, text: str):
    """Add an activity log entry."""
    session_ref.update({
        "activity": firestore.ArrayUnion([{
            "id": f"act_{uuid.uuid4().hex[:8]}",
            "type": activity_type,
            "text": text,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }])
    })


def update_agent_status(status: str):
    """Update agent_status field."""
    session_ref.update({"agent_status": status})


def update_slot_status(status: str, filled_by: str = None):
    """Update slot status and optionally who filled it."""
    updates = {"slot.status": status}
    if filled_by:
        updates["slot.filled_by"] = filled_by
    session_ref.update(updates)


def update_candidates(candidates: list[dict]):
    """Replace the candidates array."""
    session_ref.update({"candidates": candidates})


def update_recovered(amount: int):
    """Update recovered revenue."""
    session_ref.update({"recovered": amount})
```

---

## Mock Recall List (For Demo)

Use this data to score candidates:

```python
RECALL_LIST = [
    {
        "name": "Sarah Kim",
        "phone": "+1-801-555-0101",
        "treatment_needed": "cleaning",
        "days_overdue": 15,
        "reliability_score": 0.9
    },
    {
        "name": "James Park",
        "phone": "+1-801-555-0102",
        "treatment_needed": "cleaning",
        "days_overdue": 8,
        "reliability_score": 0.7
    },
    {
        "name": "Maria Garcia",
        "phone": "+1-801-555-0103",
        "treatment_needed": "filling",
        "days_overdue": 30,
        "reliability_score": 0.85
    },
    {
        "name": "David Chen",
        "phone": "+1-801-555-0104",
        "treatment_needed": "cleaning",
        "days_overdue": 5,
        "reliability_score": 0.6
    }
]
```

---

## Handoff to PM

PM's Claude Agent SDK orchestrator will:
1. Import your `brain.py` module
2. Call `score_candidates()` when a cancellation is detected
3. Call `get_next_action()` to decide what to do
4. Write outreach intent to Firestore (`pending_action`) — UI/Voice executes it
5. Read outcome from Firestore (`pending_outcome`) when UI/Voice writes it
6. Call `update_candidate_status()` with the result
7. Repeat until `get_next_action()` returns `"done"` or `"give_up"`

Your job: Make sure these functions are solid and tested. PM depends on them.

---

## Setup Checklist

- [ ] Get Firebase service account JSON from UI/Voice person
- [ ] Install: `pip install firebase-admin`
- [ ] Create `brain.py` with all functions above
- [ ] Test scoring logic with mock recall list
- [ ] Test state transitions
- [ ] Hand off to PM for integration
