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
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
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


# --- Twilio SMS ---

TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE = os.environ.get("TWILIO_PHONE_NUMBER", "")

# Phone-to-patient lookup (populated when we send SMS)
_phone_to_patient: dict[str, str] = {}

_twilio_client = None

def get_twilio():
    global _twilio_client
    if _twilio_client is None and TWILIO_SID and TWILIO_AUTH:
        from twilio.rest import Client
        _twilio_client = Client(TWILIO_SID, TWILIO_AUTH)
    return _twilio_client


def send_sms(patient: dict, slot: dict):
    """Send SMS via Twilio to the patient about the open slot."""
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
    # Track phone→patient mapping so we can match inbound replies
    _phone_to_patient[patient["phone"]] = patient["name"]
    print(f"[TWILIO] SMS sent to {patient['name']}: {msg.sid}")


@app.post("/webhooks/twilio-sms")
async def twilio_sms_webhook(request: Request):
    """Twilio inbound SMS webhook.

    Configure in Twilio Console:
      Phone Numbers → your number → Messaging →
      'A MESSAGE COMES IN' → Webhook URL:
      https://dental-agent-production.up.railway.app/webhooks/twilio-sms  (POST)
    """
    form = await request.form()
    from_number = str(form.get("From", ""))
    body_text = str(form.get("Body", ""))

    print(f"[TWILIO INBOUND] From={from_number} Body='{body_text}'")

    # Look up patient by phone number — check in-memory map first
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

    # Parse yes/no
    reply_lower = body_text.lower().strip()
    if reply_lower in ("yes", "y", "yeah", "sure", "ok", "okay", "yep", "absolutely", "yes please", "yea"):
        new_status = "confirmed"
    elif reply_lower in ("no", "n", "nope", "can't", "cannot", "no thanks", "no thank you"):
        new_status = "declined"
    else:
        new_status = "declined"

    if patient_name and _is_running:
        print(f"[TWILIO] Matched: {patient_name} → {new_status}")
        asyncio.create_task(handle_outcome_async(patient_name, new_status))
    elif not patient_name:
        print(f"[TWILIO] Could not match sender {from_number} to any patient")

    # Twilio expects TwiML — send acknowledgment
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


# --- Run directly ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
