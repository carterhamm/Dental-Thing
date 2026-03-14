"""
State machine definitions for the dental rescheduling agent.

Three state machines:
1. Candidate status - tracks each patient through the contact flow
2. Agent status - tracks the overall agent state
3. Slot status - tracks the appointment slot state
"""

# Candidate status transitions
# Each candidate goes through: waiting → calling → (outcome) → possibly texting → terminal
CANDIDATE_TRANSITIONS: dict[str, list[str]] = {
    "waiting": ["calling"],
    "calling": ["no_answer", "declined", "confirmed"],
    "no_answer": ["texting"],
    "texting": ["no_reply", "declined", "confirmed"],
    "no_reply": [],      # terminal - exhausted contact attempts
    "declined": [],      # terminal - patient said no
    "confirmed": [],     # terminal - SUCCESS, slot filled
}

# Agent status transitions
# idle → running → (complete | failed) → idle (on reset)
AGENT_TRANSITIONS: dict[str, list[str]] = {
    "idle": ["running"],
    "running": ["complete", "failed"],
    "complete": ["idle"],  # reset
    "failed": ["idle"],    # reset
}

# Slot status transitions
# open → cancelled → filling → (filled | exhausted) → open (on reset)
SLOT_TRANSITIONS: dict[str, list[str]] = {
    "open": ["cancelled"],
    "cancelled": ["filling"],
    "filling": ["filled", "exhausted"],
    "filled": ["open"],     # reset
    "exhausted": ["open"],  # reset
}

# Terminal states for candidates (no more actions possible)
TERMINAL_CANDIDATE_STATUSES = {"no_reply", "declined", "confirmed"}


def is_terminal_status(status: str) -> bool:
    """Check if a candidate status is terminal (no more actions possible)."""
    return status in TERMINAL_CANDIDATE_STATUSES


def can_transition(current: str, target: str, transitions: dict[str, list[str]]) -> bool:
    """Check if a state transition is valid."""
    allowed = transitions.get(current, [])
    return target in allowed
