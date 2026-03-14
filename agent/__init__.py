"""
Dental Rescheduling Agent - Brain Module

This package contains the core logic for the dental rescheduling agent:
- Scoring candidates from the recall list
- Decision logic for call/SMS/next actions
- State machine definitions
- Firestore write helpers
"""

from agent.brain import (
    score_candidate,
    score_candidates,
    get_next_action,
    update_candidate_status,
    calculate_recovered_revenue,
)
from agent.state import (
    CANDIDATE_TRANSITIONS,
    AGENT_TRANSITIONS,
    SLOT_TRANSITIONS,
    is_terminal_status,
)

__all__ = [
    "score_candidate",
    "score_candidates",
    "get_next_action",
    "update_candidate_status",
    "calculate_recovered_revenue",
    "CANDIDATE_TRANSITIONS",
    "AGENT_TRANSITIONS",
    "SLOT_TRANSITIONS",
    "is_terminal_status",
]
