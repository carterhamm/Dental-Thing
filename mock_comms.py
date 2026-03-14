"""
Mock comms layer — simulates ElevenLabs voice calls and Twilio SMS.

POSTs outcomes to the FastAPI webhook endpoints, just like the real
UI/Voice person's code would.

Usage:
    python mock_comms.py                     # Default: no_answer → confirmed
    python mock_comms.py --scenario demo     # no_answer → declined → confirmed
    python mock_comms.py --all-confirm       # Everyone says yes
    python mock_comms.py --all-decline       # Everyone says no

Requires the FastAPI server to be running (uvicorn main:app --port 8000).
Also requires Firebase credentials to watch for pending outreach.
"""

import sys
import time
import threading

import requests

# Where the FastAPI server is running
SERVER_URL = "http://localhost:8000"

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
_seen_actions = set()


def poll_and_handle():
    """Poll Firestore for pending_action and simulate execution."""
    from agent.firestore import init_firestore
    import os
    import firebase_admin
    from firebase_admin import firestore

    service_account_path = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "serviceAccountKey.json",
    )
    if not firebase_admin._apps:
        init_firestore(service_account_path)

    db = firestore.client()
    session_ref = db.collection("sessions").document("current")

    def on_snapshot(doc_snapshot, changes, read_time):
        global _call_count
        for doc in doc_snapshot:
            data = doc.to_dict()
            if not data:
                continue

            candidates = data.get("candidates", [])
            for candidate in candidates:
                name = candidate.get("name", "")
                status = candidate.get("status", "")
                phone = candidate.get("phone", "")

                # React to "calling" or "texting" status
                if status in ("calling", "texting") and name not in _seen_actions:
                    _seen_actions.add(name)

                    # Pick outcome from scenario
                    if _call_count < len(_scenario):
                        result = _scenario[_call_count]
                    else:
                        result = "no_answer"
                    _call_count += 1

                    channel = "voice" if status == "calling" else "sms"
                    delay = 3 if channel == "voice" else 2

                    def _handle(n=name, r=result, ch=channel, d=delay, p=phone):
                        print(f"  [{ch.upper()}] → {n} ({p})")
                        print(f"  Simulating {d}s delay...")
                        time.sleep(d)

                        if ch == "voice":
                            resp = requests.post(
                                f"{SERVER_URL}/call-outcome",
                                json={"patient_name": n, "outcome": r},
                            )
                        else:
                            reply_text = {
                                "confirmed": "YES",
                                "declined": "No thanks",
                                "no_answer": "",
                            }.get(r, "No")
                            resp = requests.post(
                                f"{SERVER_URL}/sms-reply",
                                json={"patient_name": n, "reply": reply_text},
                            )

                        print(f"  Result: {r} (server responded {resp.status_code})")
                        print()

                    thread = threading.Thread(target=_handle, daemon=True)
                    thread.start()

    session_ref.on_snapshot(on_snapshot)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

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

    print("Mock comms layer running. Watching for outreach...")
    print(f"Scenario: {_scenario}")
    print(f"Server: {SERVER_URL}")
    print()

    poll_and_handle()

    print("Press Ctrl+C to stop.\n")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nStopped.")
