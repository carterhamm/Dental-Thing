"""
Mock comms — simulates voice calls and SMS for local testing.

Watches Firestore patients collection for status changes (calling/sms_sent),
then POSTs outcomes to the FastAPI server like real Twilio/ElevenLabs would.

Usage:
    python mock_comms.py                     # Default: no_answer → confirmed
    python mock_comms.py --scenario demo     # no_answer → declined → confirmed
    python mock_comms.py --all-confirm       # Everyone says yes
    python mock_comms.py --all-decline       # Everyone says no

Requires: FastAPI server running + Firebase credentials.
"""

import sys
import time
import threading
import os

import requests
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:8000")

SCENARIOS = {
    "default": ["no_answer", "confirmed", "confirmed", "confirmed"],
    "demo": ["no_answer", "declined", "confirmed", "confirmed"],
    "all_confirm": ["confirmed", "confirmed", "confirmed", "confirmed"],
    "all_decline": ["declined", "declined", "declined", "declined"],
    "tough": ["no_answer", "no_answer", "declined", "confirmed"],
}

_call_count = 0
_scenario = SCENARIOS["default"]
_seen = set()


def watch_patients():
    """Watch the patients collection for calling/sms_sent status changes."""
    from agent.firestore import init_firestore

    service_account_path = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS", "serviceAccountKey.json"
    )
    init_firestore(service_account_path)

    import firebase_admin
    from firebase_admin import firestore

    db = firestore.client()

    def on_snapshot(col_snapshot, changes, read_time):
        global _call_count
        for change in changes:
            if change.type.name != "MODIFIED":
                continue
            doc = change.document
            data = doc.to_dict()
            name = data.get("name", "")
            status = data.get("status", "")
            phone = data.get("phone", "")

            if status in ("calling", "sms_sent") and name not in _seen:
                _seen.add(name)

                result = _scenario[_call_count] if _call_count < len(_scenario) else "no_answer"
                _call_count += 1

                channel = "voice" if status == "calling" else "sms"
                delay = 4 if channel == "voice" else 3

                def _handle(n=name, r=result, ch=channel, d=delay, p=phone):
                    print(f"  [{ch.upper()}] {n} ({p})")
                    print(f"  Waiting {d}s...")
                    time.sleep(d)

                    if ch == "voice":
                        resp = requests.post(
                            f"{SERVER_URL}/call-outcome",
                            json={"patient_name": n, "outcome": r},
                        )
                    else:
                        reply_map = {"confirmed": "YES", "declined": "No thanks", "no_answer": ""}
                        resp = requests.post(
                            f"{SERVER_URL}/sms-reply",
                            json={"patient_name": n, "reply": reply_map.get(r, "No")},
                        )

                    print(f"  → {r} (HTTP {resp.status_code})\n")

                threading.Thread(target=_handle, daemon=True).start()

    db.collection("patients").on_snapshot(on_snapshot)


if __name__ == "__main__":
    if "--all-confirm" in sys.argv:
        _scenario = SCENARIOS["all_confirm"]
    elif "--all-decline" in sys.argv:
        _scenario = SCENARIOS["all_decline"]
    elif "--scenario" in sys.argv:
        idx = sys.argv.index("--scenario")
        if idx + 1 < len(sys.argv):
            name = sys.argv[idx + 1]
            _scenario = SCENARIOS.get(name, SCENARIOS["default"])

    print(f"Mock comms | Scenario: {_scenario}")
    print(f"Server: {SERVER_URL}\n")

    watch_patients()

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\nStopped.")
