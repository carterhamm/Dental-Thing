"""
Communications layer — Twilio SMS + ElevenLabs voice.

When Twilio/ElevenLabs aren't configured, functions log to console
and return gracefully. The agent loop still works — you just feed
outcomes manually via POST /call-outcome and /sms-reply.
"""

import os
import requests

SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:8000")

# Lazy-loaded config
_twilio_client = None


def _get_twilio():
    global _twilio_client
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if not sid or not token:
        return None
    if _twilio_client is None:
        from twilio.rest import Client
        _twilio_client = Client(sid, token)
    return _twilio_client


def send_sms(to_phone: str, patient_name: str, slot_time: str, treatment: str) -> str | None:
    """Send SMS via Twilio. Returns message SID, or None if Twilio not configured."""
    client = _get_twilio()
    if client is None:
        print(f"[comms] SMS → {patient_name} ({to_phone}): (Twilio not configured, skipping)")
        return None

    from_number = os.environ.get("TWILIO_PHONE_NUMBER", "")
    body = (
        f"Hi {patient_name}, this is Bright Smile Dental. "
        f"We had a cancellation and have an opening today at {slot_time} "
        f"for a {treatment}. Would you like to take this appointment? "
        f"Reply YES to book or NO to pass."
    )

    message = client.messages.create(
        body=body,
        from_=from_number,
        to=to_phone,
        status_callback=f"{SERVER_URL}/webhooks/twilio-status",
    )
    return message.sid


def make_voice_call(to_phone: str, patient_name: str, slot_time: str, treatment: str) -> dict:
    """Make voice call via ElevenLabs. Returns result dict."""
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    agent_id = os.environ.get("ELEVENLABS_AGENT_ID", "")
    phone_id = os.environ.get("ELEVENLABS_PHONE_NUMBER_ID", "")

    if not api_key or not agent_id:
        print(f"[comms] CALL → {patient_name} ({to_phone}): (ElevenLabs not configured, skipping)")
        return {"success": False, "error": "ElevenLabs not configured"}

    response = requests.post(
        "https://api.elevenlabs.io/v1/convai/twilio/outbound-call",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "agent_id": agent_id,
            "agent_phone_number_id": phone_id,
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
        return {"success": True, "conversation_id": response.json().get("conversation_id", "")}
    return {"success": False, "error": f"{response.status_code}: {response.text[:200]}"}
