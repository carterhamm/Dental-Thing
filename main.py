"""
FastAPI server for the dental rescheduling agent.

Combines Eddy's brain logic with Spencer's Claude orchestrator.

Endpoints:
- POST /cancellation  → Triggers the Claude agent to start filling the slot
- POST /call-outcome  → Receives webhook from ElevenLabs/Twilio voice
- POST /sms-reply     → Receives webhook from Twilio SMS
- POST /reset         → Resets demo state
- GET  /              → Health check

Run with:
    uvicorn main:app --reload --port 8000
"""

import os
import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.firestore import init_firestore, reset_session
from agent.mock_data import DEMO_SLOT
from orchestrator import Orchestrator

load_dotenv()


# --- Orchestrator singleton ---
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        _orchestrator = Orchestrator(api_key)
        # Wire up comms stubs — UI/Voice person replaces these
        _orchestrator.on_voice_call = trigger_voice_call
        _orchestrator.on_sms = send_sms
    return _orchestrator


# --- App Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Firebase on startup."""
    service_account_path = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "serviceAccountKey.json",
    )
    if os.path.exists(service_account_path):
        init_firestore(service_account_path)
        print(f"Firebase initialized with {service_account_path}")
    else:
        print(f"WARNING: {service_account_path} not found. Firebase not initialized.")
        print("Set GOOGLE_APPLICATION_CREDENTIALS or place serviceAccountKey.json in project root.")
    yield


app = FastAPI(
    title="Dental Rescheduling Agent",
    description="AI agent that fills cancelled appointment slots",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Agent state ---
_is_running = False


# --- Pydantic Models ---

class CallOutcome(BaseModel):
    """Webhook payload when a voice call ends."""
    patient_name: str
    outcome: str  # "confirmed", "declined", "no_answer"


class SMSReply(BaseModel):
    """Webhook payload when an SMS reply is received."""
    patient_name: str
    reply: str  # The actual text message


# --- Endpoints ---

@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "agent_running": _is_running}


@app.post("/cancellation")
async def trigger_cancellation(background_tasks: BackgroundTasks):
    """Trigger the Claude agent to start filling a cancelled slot."""
    global _is_running
    if _is_running:
        return {"status": "already_running"}

    _is_running = True
    background_tasks.add_task(run_orchestrator)
    return {"status": "agent_started"}


@app.post("/call-outcome")
async def call_outcome(body: CallOutcome, background_tasks: BackgroundTasks):
    """Receive voice call outcome from ElevenLabs/Twilio webhook.

    UI/Voice person's code POSTs here when a call ends.
    """
    if not _is_running:
        return {"status": "agent_not_running"}

    # Map outcome string to candidate status
    status_map = {
        "confirmed": "confirmed",
        "declined": "declined",
        "no_answer": "no_answer",
    }
    new_status = status_map.get(body.outcome, "no_answer")

    # Let the orchestrator handle it (Claude decides next steps)
    background_tasks.add_task(
        handle_outcome_async, body.patient_name, new_status
    )
    return {"status": "received", "patient": body.patient_name, "outcome": body.outcome}


@app.post("/sms-reply")
async def sms_reply(body: SMSReply, background_tasks: BackgroundTasks):
    """Receive SMS reply from Twilio webhook.

    UI/Voice person's code POSTs here when a patient texts back.
    """
    if not _is_running:
        return {"status": "agent_not_running"}

    # Parse reply
    reply_lower = body.reply.lower().strip()
    if reply_lower in ("yes", "y", "yeah", "sure", "ok", "okay"):
        new_status = "confirmed"
    elif reply_lower in ("no", "n", "nope", "can't", "cannot"):
        new_status = "declined"
    else:
        new_status = "declined"

    background_tasks.add_task(
        handle_outcome_async, body.patient_name, new_status
    )
    return {"status": "received", "patient": body.patient_name, "reply": body.reply}


@app.post("/reset")
async def reset_demo():
    """Reset demo to initial state."""
    global _is_running, _orchestrator
    _is_running = False
    _orchestrator = None
    reset_session()
    return {"status": "reset_complete"}


# --- Background tasks ---

async def run_orchestrator():
    """Start the Claude orchestrator in background."""
    global _is_running
    try:
        orch = get_orchestrator()
        # run_step is sync (calls Anthropic API) — run in thread pool
        await asyncio.to_thread(orch.start, DEMO_SLOT)
    except Exception as e:
        print(f"Orchestrator error: {e}")
        from agent.firestore import update_agent_status, add_activity, update_slot_status
        update_agent_status("failed")
        update_slot_status("exhausted")
        add_activity("error", f"Agent error: {str(e)[:100]}")
        _is_running = False


async def handle_outcome_async(patient_name: str, outcome: str):
    """Handle webhook outcome — re-invoke Claude to decide next steps."""
    global _is_running
    try:
        orch = get_orchestrator()
        await asyncio.to_thread(orch.handle_outcome, patient_name, outcome)
        # Check if agent is done
        if orch.candidates:
            all_terminal = all(
                c["status"] in ("declined", "no_answer", "no_reply", "confirmed")
                for c in orch.candidates
            )
            any_confirmed = any(c["status"] == "confirmed" for c in orch.candidates)
            if any_confirmed or all_terminal:
                _is_running = False
    except Exception as e:
        print(f"Outcome handler error: {e}")
        _is_running = False


# --- Voice/SMS Stubs (UI/VOICE PERSON OWNS THESE) ---

def trigger_voice_call(patient: dict):
    """Trigger a voice call via ElevenLabs Conversational AI + Twilio.

    UI/VOICE PERSON: Replace this stub with your ElevenLabs integration.
    When the call ends, your code should POST to /call-outcome:
        POST /call-outcome
        {"patient_name": "Sarah Kim", "outcome": "confirmed"}
        outcome is one of: "confirmed", "declined", "no_answer"

    Args:
        patient: Dict with "name" and "phone" keys
    """
    print(f"[STUB] Would call {patient['name']} at {patient['phone']}")


def send_sms(patient: dict, slot: dict):
    """Send an SMS via Twilio.

    UI/VOICE PERSON: Replace this stub with your Twilio integration.
    When the patient replies, your code should POST to /sms-reply:
        POST /sms-reply
        {"patient_name": "Sarah Kim", "reply": "YES"}

    Args:
        patient: Dict with "name" and "phone" keys
        slot: Dict with appointment details
    """
    print(f"[STUB] Would SMS {patient['name']} at {patient['phone']}")


# --- Run directly ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
