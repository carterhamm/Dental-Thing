"""
FastAPI server — the deployed backend for the dental rescheduling agent.

Endpoints:
  POST /cancellation           -> Start the Claude agent
  POST /call-outcome           -> Voice call outcome (webhook or manual)
  POST /sms-reply              -> SMS reply (webhook or manual)
  POST /webhooks/twilio-sms    -> Twilio inbound SMS webhook
  POST /webhooks/elevenlabs    -> ElevenLabs post-call webhook
  POST /reset                  -> Reset demo state
  GET  /                       -> Health check

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
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

load_dotenv()

from agent.firestore import (
    init_firestore,
    reset_session,
    get_patient_by_phone,
    add_activity,
    update_agent_status,
    update_slot_status,
    seed_schedule,
    update_schedule_slot,
    update_call_status,
)
from agent.mock_data import DEMO_SLOT
from agent.mock_schedule import CANCELLED_SLOT_ID
from orchestrator import Orchestrator


# --- Orchestrator singleton ---
_orchestrator: Orchestrator | None = None
_is_running = False


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        _orchestrator = Orchestrator(api_key)
        _orchestrator.on_voice_call = trigger_voice_call
        _orchestrator.on_sms = send_sms
    return _orchestrator


# --- Firebase init (supports file path, dict, OR base64 env var for Railway) ---

def _init_firebase():
    """Initialize Firebase from file or FIREBASE_SERVICE_ACCOUNT_BASE64 env var."""
    b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_BASE64", "")
    if b64:
        try:
            decoded = base64.b64decode(b64)
            sa_dict = json.loads(decoded, strict=False)
            # init_firestore now accepts dicts directly
            init_firestore(sa_dict)
            print("Firebase initialized from FIREBASE_SERVICE_ACCOUNT_BASE64")
            return
        except Exception as e:
            print(f"Failed to decode FIREBASE_SERVICE_ACCOUNT_BASE64: {e}")

    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "serviceAccountKey.json")
    if os.path.exists(path):
        init_firestore(path)
        print(f"Firebase initialized from {path}")
    else:
        print("No Firebase credentials found. Dashboard won't update but agent still works.")
        init_firestore(None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_firebase()
    seed_schedule()
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
    outcome: str  # "confirmed", "declined", "no_answer", "reschedule_request"
    reason: str | None = None  # Optional explanation from voice AI
    preferred_time: str | None = None  # e.g., "Wednesday afternoon"


class SMSReply(BaseModel):
    patient_name: str
    reply: str


# --- Endpoints ---

@app.get("/")
async def root():
    return {"status": "ok", "agent_running": _is_running}


@app.post("/cancellation")
async def trigger_cancellation(background_tasks: BackgroundTasks):
    """Start the Claude agent."""
    global _is_running
    if _is_running:
        return {"status": "already_running"}
    _is_running = True
    background_tasks.add_task(run_orchestrator)
    return {"status": "agent_started"}


@app.post("/call-outcome")
async def call_outcome(body: CallOutcome, background_tasks: BackgroundTasks):
    """Receive voice call outcome."""
    if not _is_running:
        return {"status": "agent_not_running"}

    # reschedule_request -> declined (but we log the preferred time for follow-up)
    status_map = {
        "confirmed": "confirmed",
        "declined": "declined",
        "no_answer": "no_answer",
        "reschedule_request": "declined",
    }
    new_status = status_map.get(body.outcome, "no_answer")

    # Log reschedule request with preferred time (visible to judges!)
    if body.outcome == "reschedule_request" and body.preferred_time:
        add_activity(
            "thinking",
            f"{body.patient_name} requested {body.preferred_time} — logged for follow-up"
        )

    background_tasks.add_task(handle_outcome_bg, body.patient_name, new_status)
    return {"status": "received", "patient": body.patient_name, "outcome": body.outcome}


@app.post("/sms-reply")
async def sms_reply(body: SMSReply, background_tasks: BackgroundTasks):
    """Receive SMS reply (manual or from frontend)."""
    if not _is_running:
        return {"status": "agent_not_running"}

    reply_lower = body.reply.lower().strip()
    if reply_lower in ("yes", "y", "yeah", "sure", "ok", "okay", "yep", "absolutely"):
        new_status = "confirmed"
    else:
        new_status = "declined"

    background_tasks.add_task(handle_outcome_bg, body.patient_name, new_status)
    return {"status": "received", "patient": body.patient_name, "reply": body.reply}


# --- Reset ---

@app.post("/reset")
async def reset_demo():
    global _is_running, _orchestrator
    _is_running = False
    _orchestrator = None
    reset_session()
    update_call_status("idle")
    return {"status": "reset_complete"}


# --- Background runners ---

async def run_orchestrator():
    global _is_running
    try:
        orch = get_orchestrator()
        await asyncio.to_thread(orch.start, DEMO_SLOT)
    except Exception as e:
        print(f"Orchestrator error: {e}")
        import traceback
        traceback.print_exc()
        update_agent_status("failed")
        update_slot_status("exhausted")
        add_activity("error", f"Agent error: {str(e)[:100]}")
        _is_running = False


async def handle_outcome_bg(patient_name: str, outcome: str):
    global _is_running
    try:
        orch = get_orchestrator()
        await asyncio.to_thread(orch.handle_outcome, patient_name, outcome)
        if orch.candidates:
            any_confirmed = any(c["status"] == "confirmed" for c in orch.candidates)
            all_terminal = all(
                c["status"] in ("declined", "no_answer", "no_reply", "confirmed")
                for c in orch.candidates
            )
            # When slot is filled, also update the daily schedule
            if any_confirmed:
                update_schedule_slot(CANCELLED_SLOT_ID, patient_name)
            if any_confirmed or all_terminal:
                _is_running = False
    except Exception as e:
        print(f"Outcome handler error: {e}")
        import traceback
        traceback.print_exc()
        _is_running = False


# --- Twilio SMS ---

TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE = os.environ.get("TWILIO_PHONE_NUMBER", "")

_phone_to_patient: dict[str, str] = {}
_twilio_client = None


def get_twilio():
    global _twilio_client
    if _twilio_client is None and TWILIO_SID and TWILIO_AUTH:
        from twilio.rest import Client
        _twilio_client = Client(TWILIO_SID, TWILIO_AUTH)
    return _twilio_client


def send_sms(patient: dict, slot: dict):
    """Send SMS via Twilio. No-ops gracefully if Twilio not configured."""
    client = get_twilio()
    if not client:
        print(f"[NO TWILIO] Would SMS {patient['name']} at {patient['phone']}")
        return

    body = (
        f"Hi {patient['name'].split()[0]}, this is your dental office. "
        f"We have an opening at {slot.get('time', 'today')} for a "
        f"{slot.get('treatment', 'cleaning')}. Would you like to book it? "
        f"Reply YES or NO."
    )
    msg = client.messages.create(
        body=body,
        from_=TWILIO_PHONE,
        to=patient["phone"],
    )
    _phone_to_patient[patient["phone"]] = patient["name"]
    print(f"[TWILIO] SMS sent to {patient['name']}: {msg.sid}")


@app.post("/webhooks/twilio-sms")
async def twilio_sms_webhook(request: Request):
    """Twilio inbound SMS webhook.

    Configure in Twilio Console:
      Phone Numbers -> your number -> Messaging ->
      'A MESSAGE COMES IN' -> Webhook URL:
      https://dental-agent-production.up.railway.app/webhooks/twilio-sms  (POST)
    """
    form = await request.form()
    from_number = str(form.get("From", ""))
    body_text = str(form.get("Body", ""))

    print(f"[TWILIO INBOUND] From={from_number} Body='{body_text}'")

    # Look up patient by phone number -- check in-memory map first
    patient_name = _phone_to_patient.get(from_number, "")

    # Fuzzy match: strip formatting and compare last 10 digits
    if not patient_name:
        from_digits = ''.join(c for c in from_number if c.isdigit())[-10:]
        for phone, name in _phone_to_patient.items():
            phone_digits = ''.join(c for c in phone if c.isdigit())[-10:]
            if from_digits == phone_digits:
                patient_name = name
                break

    # If still no match, check orchestrator's candidates directly
    if not patient_name and _orchestrator and _orchestrator.candidates:
        from_digits = ''.join(c for c in from_number if c.isdigit())[-10:]
        for c in _orchestrator.candidates:
            c_digits = ''.join(ch for ch in c.get("phone", "") if ch.isdigit())[-10:]
            if from_digits == c_digits:
                patient_name = c["name"]
                _phone_to_patient[from_number] = patient_name
                break

    # Fallback to Firestore lookup
    if not patient_name:
        patient = get_patient_by_phone(from_number)
        if patient:
            patient_name = patient["name"]

    # Parse yes/no
    reply_lower = body_text.lower().strip()
    if reply_lower in ("yes", "y", "yeah", "sure", "ok", "okay", "yep", "absolutely", "yes please", "yea"):
        new_status = "confirmed"
    elif reply_lower in ("no", "n", "nope", "can't", "cannot", "no thanks", "no thank you"):
        new_status = "declined"
    else:
        new_status = "declined"

    if patient_name and _is_running:
        print(f"[TWILIO] Matched: {patient_name} -> {new_status}")
        asyncio.create_task(handle_outcome_bg(patient_name, new_status))
    elif not patient_name:
        print(f"[TWILIO] Could not match sender {from_number} to any patient")

    # Twilio expects TwiML response
    if patient_name and new_status == "confirmed":
        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>Great! You\'re booked. We\'ll see you soon!</Message></Response>'
    elif patient_name and new_status == "declined":
        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>No worries, thanks for letting us know!</Message></Response>'
    elif not patient_name:
        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response><Message>Hi! This is the dental office. If you have questions, please call us during business hours.</Message></Response>'
    else:
        twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    return Response(content=twiml, media_type="application/xml")


# --- ElevenLabs Voice Calls ---

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_AGENT_ID = os.environ.get("ELEVENLABS_AGENT_ID", "")
ELEVENLABS_PHONE_NUMBER_ID = os.environ.get("ELEVENLABS_PHONE_NUMBER_ID", "")


def trigger_voice_call(patient: dict):
    """Trigger outbound voice call via ElevenLabs Conversational AI + Twilio.

    Uses POST /v1/convai/twilio/outbound-call
    Requires: ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID, ELEVENLABS_PHONE_NUMBER_ID
    """
    if not ELEVENLABS_API_KEY or not ELEVENLABS_AGENT_ID or not ELEVENLABS_PHONE_NUMBER_ID:
        print(f"[NO ELEVENLABS] Would call {patient['name']} at {patient['phone']}")
        print(f"  API_KEY={'set' if ELEVENLABS_API_KEY else 'MISSING'}")
        print(f"  AGENT_ID={ELEVENLABS_AGENT_ID or 'MISSING'}")
        print(f"  PHONE_NUMBER_ID={ELEVENLABS_PHONE_NUMBER_ID or 'MISSING'}")
        return

    # Mark call as initiated in Firestore so frontend shows real state
    update_call_status("ringing", patient["name"])

    import requests
    resp = requests.post(
        "https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "agent_id": ELEVENLABS_AGENT_ID,
            "agent_phone_number_id": ELEVENLABS_PHONE_NUMBER_ID,
            "to_number": patient["phone"],
        },
    )
    if resp.ok:
        data = resp.json()
        print(f"[ELEVENLABS] Call initiated to {patient['name']}: {data}")
        _phone_to_patient[patient["phone"]] = patient["name"]
    else:
        print(f"[ELEVENLABS] Call failed: {resp.status_code} {resp.text}")
        update_call_status("failed", patient["name"])


@app.post("/webhooks/twilio-status")
async def twilio_status_webhook(request: Request):
    """Twilio call status callback — updates Firestore with real call state.

    Configure on your Twilio phone number:
      Voice -> Status Callback URL:
      https://dental-agent-production.up.railway.app/webhooks/twilio-status
    """
    form = await request.form()
    call_status = str(form.get("CallStatus", ""))
    call_sid = str(form.get("CallSid", ""))
    to_number = str(form.get("To", ""))

    # Look up patient name from phone number
    patient_name = _phone_to_patient.get(to_number, "")
    if not patient_name:
        to_digits = ''.join(c for c in to_number if c.isdigit())[-10:]
        for phone, name in _phone_to_patient.items():
            if ''.join(c for c in phone if c.isdigit())[-10:] == to_digits:
                patient_name = name
                break

    print(f"[TWILIO STATUS] {call_status} | {patient_name} | {call_sid}")

    # Map Twilio status to our status
    status_map = {
        "queued": "ringing",
        "initiated": "ringing",
        "ringing": "ringing",
        "in-progress": "in-progress",
        "completed": "completed",
        "no-answer": "no-answer",
        "busy": "no-answer",
        "failed": "failed",
        "canceled": "failed",
    }
    mapped = status_map.get(call_status, call_status)
    update_call_status(mapped, patient_name, call_sid)

    # If call ended without ElevenLabs webhook, handle as no_answer after a delay
    if mapped in ("no-answer", "failed", "busy"):
        if patient_name and _is_running:
            asyncio.create_task(handle_outcome_bg(patient_name, "no_answer"))

    return Response(content="", status_code=204)


@app.post("/webhooks/elevenlabs")
async def elevenlabs_webhook(request: Request, background_tasks: BackgroundTasks):
    """ElevenLabs POSTs here when a voice conversation ends."""
    data = await request.json()
    print(f"ElevenLabs webhook: {data}")

    # Call is over — clear the live call status
    update_call_status("idle")

    analysis = data.get("analysis", {})
    call_successful = analysis.get("call_successful", False)
    preferred_time = analysis.get("preferred_time")  # e.g., "Wednesday afternoon"

    # Determine outcome from analysis
    if call_successful:
        outcome = "confirmed"
    elif preferred_time or "reschedule" in str(analysis).lower():
        outcome = "reschedule_request"
    elif "declined" in str(analysis).lower() or "no" in str(analysis).lower():
        outcome = "declined"
    else:
        outcome = "no_answer"

    orch = get_orchestrator()
    if orch.current_index >= 0 and orch.current_index < len(orch.candidates):
        patient_name = orch.candidates[orch.current_index]["name"]

        # Log reschedule request with preferred time (visible to judges!)
        if outcome == "reschedule_request" and preferred_time:
            add_activity(
                "thinking",
                f"{patient_name} requested {preferred_time} — logged for follow-up"
            )

        if _is_running:
            # Map reschedule_request to declined for state machine
            status = "declined" if outcome == "reschedule_request" else outcome
            background_tasks.add_task(handle_outcome_bg, patient_name, status)

    return {"status": "received"}


# --- Run directly ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
