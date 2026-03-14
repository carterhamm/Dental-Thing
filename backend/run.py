"""
Agent entry points — HTTP trigger and Firestore watcher.

Usage:
    python run.py              # Start Flask server (HTTP trigger mode)
    python run.py --watch      # Start Firestore watcher (auto-trigger mode)
"""

import sys
import threading

from flask import Flask, jsonify
from flask_cors import CORS

from config import session_ref
from agent import run_agent
from firestore_client import get_session
from brain import RECALL_LIST

app = Flask(__name__)
CORS(app)

# Lock to prevent concurrent agent runs
_agent_lock = threading.Lock()


@app.route("/start-agent", methods=["POST"])
def start_agent():
    """HTTP trigger — UI 'Trigger Cancellation' button can call this."""
    if not _agent_lock.acquire(blocking=False):
        return jsonify({"error": "Agent already running"}), 409

    def _run():
        try:
            session = get_session()
            slot = session["slot"]
            result = run_agent(slot)
            print(f"Agent finished: {result}")
        finally:
            _agent_lock.release()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return jsonify({"status": "started"})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/session", methods=["GET"])
def session():
    """Read current session state (for debugging)."""
    return jsonify(get_session())


# ---------------------------------------------------------------------------
# Firestore watcher mode — auto-triggers when slot.status changes to cancelled
# ---------------------------------------------------------------------------

def start_watcher():
    """Watch Firestore for cancellations and auto-start the agent."""
    print("Watching Firestore for cancellations...")

    def on_snapshot(doc_snapshot, changes, read_time):
        for doc in doc_snapshot:
            data = doc.to_dict()
            if (
                data
                and data.get("slot", {}).get("status") == "cancelled"
                and data.get("agent_status") == "idle"
            ):
                print("Cancellation detected! Starting agent...")
                if _agent_lock.acquire(blocking=False):
                    def _run():
                        try:
                            result = run_agent(data["slot"])
                            print(f"Agent finished: {result}")
                        finally:
                            _agent_lock.release()

                    thread = threading.Thread(target=_run, daemon=True)
                    thread.start()

    session_ref.on_snapshot(on_snapshot)


if __name__ == "__main__":
    if "--watch" in sys.argv:
        start_watcher()
        # Keep the main thread alive
        print("Watcher running. Press Ctrl+C to stop.")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        print("Starting Flask server on :5001...")
        print("  POST /start-agent  — trigger the agent")
        print("  GET  /health       — health check")
        print("  GET  /session      — current session state")
        print()
        print("Or run with --watch to auto-trigger on cancellations.")
        app.run(host="0.0.0.0", port=5001, debug=False)
