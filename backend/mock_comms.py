"""
Mock comms layer — simulates the UI/Voice person's ElevenLabs + Twilio code.

Run this alongside agent.py to test the full loop without real phone calls.
Watches Firestore for pending_action, simulates a delay, writes pending_outcome.

Usage:
    python mock_comms.py                     # Default: first candidate no_answer, second confirmed
    python mock_comms.py --all-confirm       # Everyone says yes (first one wins)
    python mock_comms.py --all-decline       # Everyone says no (agent exhausts list)
    python mock_comms.py --scenario demo     # Demo scenario: no_answer → declined → confirmed

This is YOUR testing tool, Spencer. Delete it or ignore it once UI/Voice person's
real code is handling pending_action.
"""

import sys
import time
import threading

from config import session_ref

# Configurable scenarios
SCENARIOS = {
    "default": ["no_answer", "confirmed", "confirmed", "confirmed"],
    "demo": ["no_answer", "declined", "confirmed", "confirmed"],
    "all_confirm": ["confirmed", "confirmed", "confirmed", "confirmed"],
    "all_decline": ["declined", "declined", "declined", "declined"],
    "tough": ["no_answer", "no_answer", "declined", "confirmed"],
}

_call_count = 0
_scenario = SCENARIOS["default"]


def handle_pending_action(data: dict):
    """Simulate comms execution for a pending_action."""
    global _call_count

    action = data.get("pending_action")
    if not action or action.get("status") != "pending":
        return

    action_type = action["type"]
    patient = action["patient_name"]
    phone = action["phone"]

    # Pick outcome from scenario
    if _call_count < len(_scenario):
        result = _scenario[_call_count]
    else:
        result = "no_answer"
    _call_count += 1

    # Determine delay based on action type
    delay = 3 if action_type == "voice" else 2

    print(f"  [{action_type.upper()}] → {patient} ({phone})")
    print(f"  Simulating {delay}s delay...")

    # Mark as in_progress
    session_ref.update({"pending_action.status": "in_progress"})

    time.sleep(delay)

    # Build outcome details
    if action_type == "voice":
        details_map = {
            "confirmed": f"{patient} answered and said yes!",
            "declined": f"{patient} answered but declined.",
            "no_answer": f"Call to {patient} went unanswered after 30 seconds.",
        }
    else:
        details_map = {
            "confirmed": f'{patient} replied "YES"',
            "declined": f'{patient} replied "No thanks"',
            "no_answer": f"No reply from {patient} within timeout.",
        }

    outcome = {
        "type": action_type,
        "result": result,
        "details": details_map.get(result, f"Outcome: {result}"),
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Write outcome — PM agent will pick this up
    session_ref.update({
        "pending_outcome": outcome,
        "pending_action.status": "completed",
    })

    print(f"  Result: {result} — {outcome['details']}")
    print()


def start_mock_comms():
    """Watch Firestore for pending_action and simulate execution."""
    print("Mock comms layer running. Watching for outreach requests...")
    print(f"Scenario: {_scenario}")
    print()

    def on_snapshot(doc_snapshot, changes, read_time):
        for doc in doc_snapshot:
            data = doc.to_dict()
            if data:
                action = data.get("pending_action")
                if action and action.get("status") == "pending":
                    # Handle in a thread so the snapshot callback doesn't block
                    thread = threading.Thread(
                        target=handle_pending_action, args=(data,), daemon=True
                    )
                    thread.start()

    session_ref.on_snapshot(on_snapshot)


if __name__ == "__main__":
    # Parse scenario from args
    if "--all-confirm" in sys.argv:
        _scenario = SCENARIOS["all_confirm"]
    elif "--all-decline" in sys.argv:
        _scenario = SCENARIOS["all_decline"]
    elif "--scenario" in sys.argv:
        idx = sys.argv.index("--scenario")
        if idx + 1 < len(sys.argv):
            name = sys.argv[idx + 1]
            _scenario = SCENARIOS.get(name, SCENARIOS["default"])
            if name not in SCENARIOS:
                print(f"Unknown scenario '{name}', using default.")
                print(f"Available: {', '.join(SCENARIOS.keys())}")

    start_mock_comms()
    print("Press Ctrl+C to stop.\n")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nStopped.")
