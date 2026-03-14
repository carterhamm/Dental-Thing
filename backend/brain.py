"""
brain.py — Scoring logic, decision rules, and state transitions.

OWNER: Eddy
CONSUMERS: Spencer's agent.py (imports and calls these functions)

Eddy: implement every function below. The signatures, types, and docstrings
are the contract — don't change them without syncing with Spencer.
The agent depends on exact return shapes.

Run `python -m pytest test_brain.py -v` to validate your implementation.
"""

from typing import Literal

CandidateStatus = Literal[
    "waiting", "calling", "texting", "declined", "no_answer", "confirmed"
]
Action = Literal["call", "sms", "next_candidate", "give_up", "done"]


def score_candidates(recall_list: list[dict], slot: dict) -> list[dict]:
    """Score and rank candidates for a given slot.

    Args:
        recall_list: Patients from recall list. Each dict has:
            - name: str
            - phone: str
            - treatment_needed: str
            - days_overdue: int
            - reliability_score: float (0.0 to 1.0)
        slot: The slot to fill:
            - treatment: str
            - time: str
            - date: str
            - value: int

    Returns:
        Ranked list (highest score first), each dict has:
            - rank: int (1-indexed)
            - name: str
            - phone: str
            - score: int (0-100)
            - status: "waiting" (always — they haven't been contacted yet)
            - treatment_needed: str
            - days_overdue: int

    Scoring factors (suggested weights — tune as you see fit):
        - Days overdue: more overdue = higher score
        - Treatment match: candidate needs same treatment as slot = big bonus
        - Reliability: higher reliability_score = bonus
        - Cap at 100

    Example output:
        [
            {"rank": 1, "name": "Sarah Kim", "phone": "+1-801-555-0101",
             "score": 82, "status": "waiting", "treatment_needed": "cleaning",
             "days_overdue": 15},
            ...
        ]
    """
    raise NotImplementedError("Eddy: implement this")


def get_next_action(
    candidates: list[dict], current_candidate_index: int
) -> tuple[Action, int]:
    """Decide the next action based on current candidate statuses.

    Args:
        candidates: Current ranked candidate list (from score_candidates,
            with statuses updated over time).
        current_candidate_index: Index of candidate we're working on.
            Pass -1 on first call (no candidate yet).

    Returns:
        (action, candidate_index) tuple:
            ("call", 0)           → Voice-call candidate at index 0
            ("sms", 0)            → SMS candidate at index 0 (fallback after no_answer on call)
            ("next_candidate", 1) → Skip to candidate at index 1
            ("give_up", -1)       → All candidates exhausted
            ("done", 0)           → Candidate at index 0 confirmed, slot filled

    Decision logic:
        1. If any candidate has status "confirmed" → ("done", that_index)
        2. If current_candidate_index == -1 → start with index 0, ("call", 0)
        3. Current candidate status:
            - "waiting" → ("call", current_index)
            - "calling" or "no_answer" → ("sms", current_index)
            - "texting" → ("next_candidate", current_index + 1)  [SMS didn't work]
            - "declined" → ("next_candidate", current_index + 1)
        4. If next_candidate index >= len(candidates) → ("give_up", -1)
    """
    raise NotImplementedError("Eddy: implement this")


def update_candidate_status(
    candidates: list[dict], candidate_index: int, new_status: CandidateStatus
) -> list[dict]:
    """Update a candidate's status and return the updated list.

    Args:
        candidates: Current candidate list
        candidate_index: Which candidate to update (0-indexed)
        new_status: New status value

    Returns:
        New list with the candidate's status updated.
        Does NOT mutate the input list.
    """
    raise NotImplementedError("Eddy: implement this")


def calculate_recovered_revenue(slot: dict) -> int:
    """Return the dollar value recovered when a slot is filled."""
    return slot.get("value", 0)


# ---------------------------------------------------------------------------
# Mock recall list — shared with seed.py. Eddy, feel free to add more
# patients or adjust scores, but keep at least these 4 for demo consistency.
# ---------------------------------------------------------------------------
RECALL_LIST = [
    {
        "name": "Sarah Kim",
        "phone": "+1-801-555-0101",
        "treatment_needed": "cleaning",
        "days_overdue": 15,
        "reliability_score": 0.9,
    },
    {
        "name": "James Park",
        "phone": "+1-801-555-0102",
        "treatment_needed": "cleaning",
        "days_overdue": 8,
        "reliability_score": 0.7,
    },
    {
        "name": "Maria Garcia",
        "phone": "+1-801-555-0103",
        "treatment_needed": "filling",
        "days_overdue": 30,
        "reliability_score": 0.85,
    },
    {
        "name": "David Chen",
        "phone": "+1-801-555-0104",
        "treatment_needed": "cleaning",
        "days_overdue": 5,
        "reliability_score": 0.6,
    },
]
