"""
Real communications layer — Twilio SMS + ElevenLabs Conversational AI voice calls.

This module makes actual phone calls and sends actual text messages.
Judges will receive these on their real phones.

Setup required:
  - Twilio account with a phone number
  - ElevenLabs account with a Conversational AI agent + Twilio phone number imported
  - See .env.example for all required env vars
"""

import os
import requests
from twilio.rest import Client as TwilioClient


# --- Config (loaded from env) ---

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_AGENT_ID = os.environ.get("ELEVENLABS_AGENT_ID", "")
ELEVENLABS_PHONE_NUMBER_ID = os.environ.get("ELEVENLABS_PHONE_NUMBER_ID", "")

# The public URL of our FastAPI server (set after deploying to Railway)
# Twilio needs this to send SMS reply webhooks
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:8000")


def _get_twilio_client() -> TwilioClient:
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError("Twilio credentials not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN.")
    return TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# --- SMS ---

def send_sms(to_phone: str, patient_name: str, slot_time: str, treatment: str) -> str:
    """Send a real SMS via Twilio.

    Returns the Twilio message SID.
    """
    client = _get_twilio_client()

    body = (
        f"Hi {patient_name}, this is Bright Smile Dental. "
        f"We had a cancellation and have an opening today at {slot_time} "
        f"for a {treatment}. Would you like to take this appointment? "
        f"Reply YES to book or NO to pass."
    )

    message = client.messages.create(
        body=body,
        from_=TWILIO_PHONE_NUMBER,
        to=to_phone,
        status_callback=f"{SERVER_URL}/webhooks/twilio-status",
    )

    return message.sid


# --- Voice Calls (ElevenLabs Conversational AI) ---

def make_voice_call(
    to_phone: str,
    patient_name: str,
    slot_time: str,
    treatment: str,
) -> dict:
    """Make a real phone call via ElevenLabs Conversational AI + Twilio.

    ElevenLabs handles the entire conversation autonomously:
    - Introduces itself as the dental office
    - Explains the cancellation opening
    - Handles the patient's response (yes, no, questions)
    - The conversation outcome arrives via webhook to /webhooks/elevenlabs

    Returns: {"conversation_id": str, "success": bool}
    """
    if not ELEVENLABS_API_KEY or not ELEVENLABS_AGENT_ID:
        raise RuntimeError("ElevenLabs not configured. Set ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID.")

    response = requests.post(
        "https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "agent_id": ELEVENLABS_AGENT_ID,
            "agent_phone_number_id": ELEVENLABS_PHONE_NUMBER_ID,
            "to_number": to_phone,
            "conversation_initiation_client_data": {
                "dynamic_variables": {
                    "patient_name": patient_name,
                    "slot_time": slot_time,
                    "treatment": treatment,
                },
            },
        },
        timeout=30,
    )

    if response.status_code == 200:
        data = response.json()
        return {
            "success": True,
            "conversation_id": data.get("conversation_id", ""),
        }
    else:
        return {
            "success": False,
            "error": f"ElevenLabs API returned {response.status_code}: {response.text[:200]}",
        }


def get_conversation_result(conversation_id: str) -> dict | None:
    """Poll ElevenLabs for conversation outcome (backup if webhook doesn't fire).

    Returns analysis dict or None if not ready yet.
    """
    if not ELEVENLABS_API_KEY:
        return None

    response = requests.get(
        f"https://api.elevenlabs.io/v1/convai/conversations/{conversation_id}",
        headers={"xi-api-key": ELEVENLABS_API_KEY},
        timeout=10,
    )

    if response.status_code == 200:
        data = response.json()
        status = data.get("status", "")
        if status in ("done", "completed"):
            return {
                "status": status,
                "analysis": data.get("analysis", {}),
                "transcript": data.get("transcript", ""),
            }
    return None
