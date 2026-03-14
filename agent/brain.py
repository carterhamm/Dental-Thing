"""
Core decision logic for the dental rescheduling agent.

This module is the "brain" that PM's Claude SDK agent will call.
It handles:
- Scoring candidates from the recall list
- Deciding the next action (call, SMS, next candidate, etc.)
- Updating candidate statuses
"""

from typing import Literal

from agent.state import is_terminal_status

# Type definitions
Action = Literal["call", "sms", "next_candidate", "wait", "give_up", "done"]
CandidateStatus = Literal[
    "waiting", "calling", "no_answer", "texting", "no_reply", "declined", "confirmed"
]

# Timeout configurations (in seconds)
# For demo, these can be shortened to keep things snappy
CALL_TIMEOUT = 30.0  # How long to wait for call outcome
SMS_TIMEOUT = 60.0   # How long to wait for SMS reply


def score_candidate(patient: dict, slot: dict) -> int:
    """
    Score a patient for a given slot.

    Higher score = higher priority to contact.

    Scoring factors:
    1. Cycles overdue × 40: More cycles missed = higher urgency
    2. Treatment match: +50 bonus / -20 penalty
    3. Reliability × 20: More reliable patients get bonus
    4. Time of day match: +10 if patient's preferred time matches slot
    5. Pending treatment: +25 if patient has unfinished treatment

    Args:
        patient: Patient dict with keys:
            - treatment_needed: str
            - cycles_overdue: int
            - reliability_score: float (0-1)
            - preferred_time_of_day: "morning" | "afternoon" | "evening"
            - pending_treatment: bool
        slot: Slot dict with keys:
            - treatment: str
            - time: str (e.g., "2:00 PM")

    Returns:
        Integer score (higher = better candidate)
    """
    score = 0

    # Cycles overdue: each missed cycle adds urgency (capped at 4 cycles)
    cycles = min(patient.get("cycles_overdue", 1), 4)
    score += cycles * 25

    # Treatment match is still the dominant factor
    # You can't do a crown in a cleaning slot
    if patient["treatment_needed"] == slot["treatment"]:
        score += 100
    else:
        score -= 50

    # Reliability bonus (scaled to 0-20 range)
    score += int(patient.get("reliability_score", 0.5) * 20)

    # Time of day matching
    slot_time = slot.get("time", "12:00 PM")
    slot_tod = _get_time_of_day(slot_time)
    if patient.get("preferred_time_of_day") == slot_tod:
        score += 10

    # Pending treatment bonus (urgency for unfinished work)
    if patient.get("pending_treatment", False):
        score += 25

    return score


def _get_time_of_day(time_str: str) -> str:
    """
    Convert a time string to time of day category.

    Args:
        time_str: Time like "2:00 PM" or "10:30 AM"

    Returns:
        "morning" (before 12pm), "afternoon" (12pm-5pm), or "evening" (after 5pm)
    """
    # Parse hour from time string
    time_str = time_str.upper().strip()
    try:
        # Handle "2:00 PM" format
        if "PM" in time_str:
            hour = int(time_str.split(":")[0])
            if hour != 12:
                hour += 12
        else:  # AM
            hour = int(time_str.split(":")[0])
            if hour == 12:
                hour = 0
    except (ValueError, IndexError):
        return "afternoon"  # Default

    if hour < 12:
        return "morning"
    elif hour < 17:  # 5 PM
        return "afternoon"
    else:
        return "evening"


def score_candidates(recall_list: list[dict], slot: dict) -> list[dict]:
    """
    Score and rank all candidates for a slot.

    Args:
        recall_list: List of patients from recall list
        slot: The slot to fill

    Returns:
        List of candidates sorted by score (highest first), with added fields:
            - rank: int (1-indexed)
            - score: int
            - status: "waiting"
    """
    # Score each patient
    scored = []
    for patient in recall_list:
        candidate = {
            "name": patient["name"],
            "phone": patient["phone"],
            "treatment_needed": patient["treatment_needed"],
            "cycles_overdue": patient.get("cycles_overdue", 1),
            "reliability_score": patient.get("reliability_score", 0.5),
            "preferred_time_of_day": patient.get("preferred_time_of_day", "afternoon"),
            "pending_treatment": patient.get("pending_treatment", False),
            "score": score_candidate(patient, slot),
            "status": "waiting",
        }
        scored.append(candidate)

    # Sort by score descending
    scored.sort(key=lambda c: c["score"], reverse=True)

    # Add rank
    for i, candidate in enumerate(scored):
        candidate["rank"] = i + 1

    return scored


def get_next_action(
    candidates: list[dict],
    current_index: int,
    elapsed_time: float = 0.0,
) -> tuple[Action, int]:
    """
    Decide the next action based on current state.

    This is the core decision function. PM's agent loop calls this repeatedly
    to drive the flow.

    Args:
        candidates: Current ranked candidate list with statuses
        current_index: Index of candidate we're currently working on (-1 if none)
        elapsed_time: Seconds elapsed since current action started (for timeout checks)

    Returns:
        (action, candidate_index) tuple:
        - ("call", idx) → Trigger voice call to candidate at idx
        - ("sms", idx) → Send SMS to candidate at idx
        - ("next_candidate", idx) → Move to next candidate at idx
        - ("wait", idx) → Still waiting for response, check again later
        - ("give_up", -1) → All candidates exhausted, slot unfilled
        - ("done", idx) → Candidate confirmed, slot filled!
    """
    if not candidates:
        return ("give_up", -1)

    # Check if any candidate is confirmed (slot filled!)
    for i, c in enumerate(candidates):
        if c["status"] == "confirmed":
            return ("done", i)

    # If no current candidate, start with first one
    if current_index < 0:
        return ("call", 0)

    # Check if current index is valid
    if current_index >= len(candidates):
        return ("give_up", -1)

    current = candidates[current_index]
    status = current["status"]

    # Decision tree based on current candidate's status
    if status == "waiting":
        # Haven't contacted yet → call them
        return ("call", current_index)

    elif status == "calling":
        # Currently calling → check timeout
        if elapsed_time >= CALL_TIMEOUT:
            # Timeout → will need to mark as no_answer and try SMS
            return ("sms", current_index)
        else:
            # Still waiting for call outcome
            return ("wait", current_index)

    elif status == "no_answer":
        # Call failed → try SMS
        return ("sms", current_index)

    elif status == "texting":
        # Currently texting → check timeout
        if elapsed_time >= SMS_TIMEOUT:
            # Timeout → move to next candidate
            return _try_next_candidate(candidates, current_index)
        else:
            # Still waiting for SMS reply
            return ("wait", current_index)

    elif status in ("no_reply", "declined"):
        # Terminal failure → try next candidate
        return _try_next_candidate(candidates, current_index)

    elif status == "confirmed":
        # Should have been caught above, but just in case
        return ("done", current_index)

    else:
        # Unknown status → try next candidate to be safe
        return _try_next_candidate(candidates, current_index)


def _try_next_candidate(candidates: list[dict], current_index: int) -> tuple[Action, int]:
    """
    Find the next non-terminal candidate to try.

    Returns ("next_candidate", idx) if found, ("give_up", -1) if all exhausted.
    """
    for i in range(current_index + 1, len(candidates)):
        if not is_terminal_status(candidates[i]["status"]):
            return ("next_candidate", i)

    # All remaining candidates are terminal
    return ("give_up", -1)


def update_candidate_status(
    candidates: list[dict],
    candidate_index: int,
    new_status: CandidateStatus,
) -> list[dict]:
    """
    Update a candidate's status and return the updated list.

    Creates a new list (doesn't mutate in place) for cleaner state management.

    Args:
        candidates: Current candidate list
        candidate_index: Which candidate to update
        new_status: New status value

    Returns:
        New candidate list with updated status
    """
    # Create a copy to avoid mutating the original
    updated = [c.copy() for c in candidates]
    updated[candidate_index]["status"] = new_status
    return updated


def calculate_recovered_revenue(slot: dict) -> int:
    """
    Calculate recovered revenue when a slot is filled.

    Args:
        slot: The slot that was filled

    Returns:
        Dollar amount recovered (slot value)
    """
    return slot.get("value", 0)


# Re-export mock data for backwards compatibility (tests import from here)
from agent.mock_data import RECALL_LIST, DEMO_SLOT
