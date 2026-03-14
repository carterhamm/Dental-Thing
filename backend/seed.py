"""
Seed / reset Firestore to clean demo state.

Usage:
    python seed.py          # seed initial state
    python seed.py --reset  # same thing (alias for clarity during demo)

Safe to run repeatedly — overwrites sessions/current entirely.
"""

import sys
from config import session_ref

INITIAL_SESSION = {
    "slot": {
        "id": "slot_001",
        "time": "2:00 PM",
        "date": "Today",
        "treatment": "cleaning",
        "value": 200,
        "status": "open",
        "filled_by": None,
    },
    "activity": [],
    "candidates": [],
    "pending_action": None,
    "pending_outcome": None,
    "recovered": 0,
    "agent_status": "idle",
}


def seed():
    """Write clean demo state to Firestore."""
    session_ref.set(INITIAL_SESSION)
    print("Firestore seeded: sessions/current → clean demo state")
    print(f"  slot: {INITIAL_SESSION['slot']['time']} {INITIAL_SESSION['slot']['treatment']}")
    print(f"  status: {INITIAL_SESSION['slot']['status']}")
    print(f"  agent: {INITIAL_SESSION['agent_status']}")


if __name__ == "__main__":
    seed()
