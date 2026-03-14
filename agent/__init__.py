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
from agent.mock_data import RECALL_LIST, DEMO_SLOT
from agent.firestore import (
    init_firestore,
    initialize_session,
    add_activity,
    update_agent_status,
    update_slot_status,
    update_candidates,
    update_recovered,
    reset_session,
    get_patient_by_phone,
)

__all__ = [
    # Brain logic
    "score_candidate",
    "score_candidates",
    "get_next_action",
    "update_candidate_status",
    "calculate_recovered_revenue",
    # State machines
    "CANDIDATE_TRANSITIONS",
    "AGENT_TRANSITIONS",
    "SLOT_TRANSITIONS",
    "is_terminal_status",
    # Mock data
    "RECALL_LIST",
    "DEMO_SLOT",
    # Firestore helpers
    "init_firestore",
    "initialize_session",
    "add_activity",
    "update_agent_status",
    "update_slot_status",
    "update_candidates",
    "update_recovered",
    "reset_session",
    "get_patient_by_phone",
]
