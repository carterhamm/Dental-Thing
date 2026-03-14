# CLAUDE-BE.md — Backend Logic (Eddy)

## Project Overview

Dental rescheduling agent that autonomously fills cancelled appointment slots. When a patient cancels, the AI agent scores candidates, contacts them via voice/SMS, and keeps going until the slot is filled.

**Your role:** Own the scoring logic, decision rules, state transitions, and Firestore schema design. You are the "brain" — PM's Claude Agent SDK orchestrator will call your functions to decide what to do.

---

## Firestore Schema (Adapted to Carter's Frontend)

Backend writes to these collections. Frontend listens in real-time.

### Collection: `slots` → Document: `active`

```json
{
  "id": "slot_001",
  "time": "2:00 PM",
  "date": "Today",
  "treatment": "cleaning",
  "value": 200,
  "status": "filling",
  "filled_by": null
}
```

### Collection: `agent` → Document: `status`

```json
{
  "status": "running",
  "recovered": 0
}
```

### Collection: `patients` → Documents: `p0`, `p1`, `p2`, ...

Each candidate is a separate document for real-time UI updates:

```json
{
  "rank": 1,
  "name": "Sarah Kim",
  "phone": "+1-801-555-0101",
  "score": 154,
  "status": "calling",
  "treatment_needed": "cleaning",
  "cycles_overdue": 1,
  "reliability_score": 0.95,
  "preferred_time_of_day": "afternoon",
  "pending_treatment": false
}
```

### Collection: `activity_log` → Auto-generated documents

```json
{
  "id": "act_abc123",
  "type": "thinking",
  "text": "Scoring 16 candidates for cleaning",
  "timestamp": "<serverTimestamp>"
}
```

### `slot.status` Values

| Value | Meaning |
|-------|---------|
| `"open"` | Normal scheduled slot |
| `"cancelled"` | Patient cancelled, agent not yet started |
| `"filling"` | Agent is actively working to fill |
| `"filled"` | Slot has been filled |
| `"exhausted"` | Agent tried all candidates, nobody available |

### `agent.status` Values

| Value | Meaning |
|-------|---------|
| `"idle"` | Waiting for a cancellation |
| `"running"` | Actively filling a slot |
| `"complete"` | Slot filled successfully |
| `"failed"` | Could not fill slot (exhausted candidates) |

### `activity_log.type` Values

| Type | When to Use |
|------|-------------|
| `"event"` | System events (cancellation received, agent started) |
| `"thinking"` | Agent reasoning (scoring candidates, deciding next step) |
| `"tool_call"` | Agent taking action (requesting call/SMS) |
| `"call_outcome"` | Result of a voice call |
| `"sms_sent"` | SMS was sent |
| `"success"` | Slot filled, revenue logged |
| `"error"` | Something went wrong |

### `patients.status` Values

| Value | Meaning |
|-------|---------|
| `"waiting"` | Not yet contacted |
| `"calling"` | Currently being called |
| `"texting"` | SMS sent, waiting for reply |
| `"declined"` | Said no |
| `"no_answer"` | Didn't pick up |
| `"no_reply"` | SMS sent, no response |
| `"confirmed"` | Said yes — slot filled |

---

## Your Module: `agent/brain.py`

PM's orchestrator imports and calls these functions.

### Scoring Formula

```python
def score_candidate(patient: dict, slot: dict) -> int:
    """
    Scoring factors:
    - cycles_overdue × 25 (capped at 4 cycles, max 100 pts)
    - treatment_match: +100 / -50 (dominant factor)
    - reliability × 20 (0-20 pts)
    - time_of_day match: +10 if preferred time matches slot
    - pending_treatment: +25 if unfinished treatment
    """
```

### Function Signatures

```python
from typing import Literal

Action = Literal["call", "sms", "next_candidate", "wait", "give_up", "done"]
CandidateStatus = Literal["waiting", "calling", "texting", "declined", "no_answer", "no_reply", "confirmed"]

def score_candidates(recall_list: list[dict], slot: dict) -> list[dict]:
    """Score and rank candidates. Returns sorted list with score, rank, status."""

def get_next_action(candidates: list[dict], current_index: int, elapsed_time: float = 0.0) -> tuple[Action, int]:
    """Decide next action based on current state. Includes timeout handling."""

def update_candidate_status(candidates: list[dict], idx: int, new_status: CandidateStatus) -> list[dict]:
    """Update a candidate's status (immutable - returns new list)."""

def calculate_recovered_revenue(slot: dict) -> int:
    """Return slot value when filled."""
```

---

## Firestore Helpers: `agent/firestore.py`

```python
def init_firestore(service_account_path: str) -> None
def initialize_session(slot: dict, recall_list: list = None) -> list[dict]  # Main entry point!
def add_activity(activity_type: str, text: str) -> None
def update_agent_status(status: str) -> None
def update_slot_status(status: str, filled_by: str = None) -> None
def update_candidates(candidates: list[dict]) -> None
def update_recovered(amount: int) -> None
def reset_session() -> None
```

### Quick Start for PM

```python
from agent import initialize_session, DEMO_SLOT

# When cancellation happens:
candidates = initialize_session(DEMO_SLOT)
# This automatically:
# - Scores all 16 patients
# - Writes slot, agent status, candidates to Firestore
# - Logs activity
# - Returns ranked candidates
```

---

## Patient Data Fields

```python
{
    "name": "Sarah Kim",
    "phone": "+1-801-555-0101",
    "treatment_needed": "cleaning",
    "cycles_overdue": 1,              # 1 cycle = ~6 months for cleanings
    "reliability_score": 0.95,        # 0-1 based on appointment history
    "preferred_time_of_day": "afternoon",  # "morning" | "afternoon" | "evening"
    "pending_treatment": False,       # True if unfinished treatment
}
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

## Mock Data

16 patients across 6 treatment types in `agent/mock_data.py`:
- 5 cleaning patients
- 3 filling patients
- 2 crown patients
- 2 root canal patients
- 2 exam patients
- 2 whitening patients

4 patients have `pending_treatment: True` (unfinished work).

---

## Setup Checklist

- [x] Get Firebase service account JSON from UI/Voice person
- [x] Install: `pip install firebase-admin`
- [x] Create `brain.py` with all functions
- [x] Test scoring logic with mock recall list (20 tests passing)
- [x] Test state transitions
- [x] Adapt to Carter's Firestore schema
- [x] Create `initialize_session()` for PM integration
- [x] Hand off to PM for integration

---

## Files

```
agent/
├── __init__.py          # Package exports
├── brain.py             # Scoring + decision logic
├── state.py             # State machine definitions
├── firestore.py         # Firestore write helpers
├── mock_data.py         # 16 mock patients + demo slots
└── tests/
    └── test_brain.py    # 20 tests
```
