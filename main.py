"""
FastAPI server — the deployed backend for the dental rescheduling agent.

Endpoints:
  POST /cancellation           → Start the Claude agent
  POST /call-outcome           → ElevenLabs webhook (voice call ended)
  POST /sms-reply              → App-level SMS reply (from frontend or test)
  POST /webhooks/twilio-sms    → Twilio inbound SMS webhook (real texts)
  POST /webhooks/elevenlabs    → ElevenLabs post-call webhook
  POST /reset                  → Reset demo state
  GET  /                       → Health check

Deploy to Railway:
  railway up
  # Set env vars in Railway dashboard

Run locally:
  uvicorn main:app --reload --port 8000
"""

import os
import json
import base64
import tempfile
import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

load_dotenv()

from agent.firestore import init_firestore, reset_session, get_patient_by_phone
from orchestrator import Orchestrator
from comms import send_sms, make_voice_call


# --- Orchestrator singleton ---
_orchestrator: Orchestrator | None = None
_is_running = False

SLOT = {
    "time": "2:30 PM",
    "date": "today",
    "treatment": "cleaning",
    "value": 185,
}


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        _orchestrator = Orchestrator(api_key)
        _orchestrator.on_voice_call = _do_voice_call
        _orchestrator.on_sms = _do_sms
    return _orchestrator


# --- Comms callbacks (graceful when not configured) ---

def _do_voice_call(candidate: dict) -> None:
    try:
        result = make_voice_call(
            to_phone=candidate["phone"],
            patient_name=candidate["name"],
            slot_time=SLOT["time"],
            treatment=SLOT["treatment"],
        )
        if not result["success"]:
            print(f"Voice call note: {result.get('error')}")
    except Exception as e:
        print(f"Voice call error: {e}")


def _do_sms(candidate: dict, slot: dict) -> None:
    try:
        sid = send_sms(
            to_phone=candidate["phone"],
            patient_name=candidate["name"],
            slot_time=slot.get("time", SLOT["time"]),
            treatment=slot.get("treatment", SLOT["treatment"]),
        )
        if sid:
            print(f"SMS sent: {sid}")
    except Exception as e:
        print(f"SMS error: {e}")


# --- Firebase init (supports file path OR base64 env var for Railway) ---

def _init_firebase():
    """Initialize Firebase from file or FIREBASE_SERVICE_ACCOUNT_BASE64 env var."""
    # Option 1: base64-encoded service account JSON (for Railway/cloud deploy)
    b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_BASE64", "")
    if b64:
        try:
            decoded = base64.b64decode(b64)
            sa_dict = json.loads(decoded)
            # Write to temp file for firebase-admin
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump(sa_dict, tmp)
            tmp.close()
            init_firestore(tmp.name)
            print("Firebase initialized from FIREBASE_SERVICE_ACCOUNT_BASE64")
            return
        except Exception as e:
            print(f"Failed to decode FIREBASE_SERVICE_ACCOUNT_BASE64: {e}")

    # Option 2: file path
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "serviceAccountKey.json")
    if os.path.exists(path):
        init_firestore(path)
        print(f"Firebase initialized from {path}")
    else:
        print(f"No Firebase credentials found. Dashboard won't update but agent still works.")
        init_firestore(None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_firebase()
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


# --- Models ---

class CallOutcome(BaseModel):
    patient_name: str
    outcome: str  # "confirmed", "declined", "no_answer"


class SMSReply(BaseModel):
    patient_name: str
    reply: str


# --- Endpoints ---

@app.get("/")
async def root():
    return {"status": "ok", "agent_running": _is_running}


@app.post("/cancellation")
async def trigger_cancellation(background_tasks: BackgroundTasks):
    """Start the Claude agent. Called by frontend or test."""
    global _is_running
    if _is_running:
        return {"status": "already_running"}
    _is_running = True
    background_tasks.add_task(run_orchestrator)
    return {"status": "agent_started"}


@app.post("/call-outcome")
async def call_outcome(body: CallOutcome, background_tasks: BackgroundTasks):
    """Receive voice call outcome. Called by ElevenLabs webhook handler or test."""
    if not _is_running:
        return {"status": "agent_not_running"}

    status_map = {"confirmed": "confirmed", "declined": "declined", "no_answer": "no_answer"}
    new_status = status_map.get(body.outcome, "no_answer")

    background_tasks.add_task(handle_outcome_bg, body.patient_name, new_status)
    return {"status": "received", "patient": body.patient_name}


@app.post("/sms-reply")
async def sms_reply(body: SMSReply, background_tasks: BackgroundTasks):
    """Receive SMS reply. Called by Twilio webhook handler or test."""
    if not _is_running:
        return {"status": "agent_not_running"}

    reply_lower = body.reply.lower().strip()
    if reply_lower in ("yes", "y", "yeah", "sure", "ok", "okay", "yep"):
        new_status = "confirmed"
    else:
        new_status = "declined"

    background_tasks.add_task(handle_outcome_bg, body.patient_name, new_status)
    return {"status": "received", "patient": body.patient_name}


# --- Real Twilio Inbound SMS Webhook ---

@app.post("/webhooks/twilio-sms")
async def twilio_sms_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Twilio POSTs here when a patient replies to our SMS.

    Twilio sends application/x-www-form-urlencoded with fields:
    Body, From, To, MessageSid, etc.
    """
    form = await request.form()
    body_text = form.get("Body", "")
    from_phone = form.get("From", "")

    print(f"Twilio SMS from {from_phone}: {body_text}")

    # Look up which patient this is by phone number
    patient = get_patient_by_phone(from_phone)
    if patient and _is_running:
        reply_lower = body_text.lower().strip()
        if reply_lower in ("yes", "y", "yeah", "sure", "ok", "okay", "yep"):
            new_status = "confirmed"
        else:
            new_status = "declined"
        background_tasks.add_task(handle_outcome_bg, patient["name"], new_status)

    # Twilio requires a TwiML response
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
    )


# --- ElevenLabs Post-Call Webhook ---

@app.post("/webhooks/elevenlabs")
async def elevenlabs_webhook(request: Request, background_tasks: BackgroundTasks):
    """ElevenLabs POSTs here when a voice conversation ends."""
    data = await request.json()
    print(f"ElevenLabs webhook: {data}")

    conversation_id = data.get("conversation_id", "")
    analysis = data.get("analysis", {})
    transcript = data.get("transcript", "")

    # Try to determine outcome from analysis
    call_successful = analysis.get("call_successful", False)
    if call_successful:
        outcome = "confirmed"
    elif "declined" in str(analysis).lower() or "no" in str(analysis).lower():
        outcome = "declined"
    else:
        outcome = "no_answer"

    # We need the patient name — check if orchestrator has it
    orch = get_orchestrator()
    if orch.current_index >= 0 and orch.current_index < len(orch.candidates):
        patient_name = orch.candidates[orch.current_index]["name"]
        if _is_running:
            background_tasks.add_task(handle_outcome_bg, patient_name, outcome)

    return {"status": "received"}


# --- Reset ---

@app.post("/reset")
async def reset_demo():
    global _is_running, _orchestrator
    _is_running = False
    _orchestrator = None
    reset_session()
    return {"status": "reset_complete"}


# --- Background runners ---

async def run_orchestrator():
    global _is_running
    try:
        orch = get_orchestrator()
        await asyncio.to_thread(orch.start, SLOT)
    except Exception as e:
        print(f"Orchestrator error: {e}")
        import traceback
        traceback.print_exc()
        from agent.firestore import add_activity, update_agent_phase
        update_agent_phase("idle")
        add_activity("❌", f"Agent error: {str(e)[:100]}", "warning")
        _is_running = False


async def handle_outcome_bg(patient_name: str, outcome: str):
    global _is_running
    try:
        orch = get_orchestrator()
        await asyncio.to_thread(orch.handle_outcome, patient_name, outcome)
        # Check if done
        if orch.candidates:
            any_confirmed = any(c["status"] == "confirmed" for c in orch.candidates)
            all_terminal = all(
                c["status"] in ("declined", "no_answer", "no_reply", "confirmed")
                for c in orch.candidates
            )
            if any_confirmed or all_terminal:
                _is_running = False
    except Exception as e:
        print(f"Outcome handler error: {e}")
        import traceback
        traceback.print_exc()
        _is_running = False


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
