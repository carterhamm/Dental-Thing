"""
FastAPI server for the dental rescheduling agent.

This is the "body" that runs the brain. It exposes endpoints for:
- POST /cancellation  → Triggers the agent loop
- POST /call-outcome  → Receives webhook from Bland.ai
- POST /sms-reply     → Receives webhook from Twilio
- POST /reset         → Resets demo state

Run with:
    uvicorn main:app --reload --port 8000
"""

import asyncio
import os
import time

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.brain import (
    score_candidates,
    get_next_action,
    update_candidate_status,
)
from agent.firestore import (
    init_firestore,
    add_activity,
    update_agent_status,
    update_slot_status,
    update_candidates,
    update_recovered,
    reset_session,
)
from agent.mock_data import RECALL_LIST, DEMO_SLOT


# --- App Setup ---

app = FastAPI(
    title="Dental Rescheduling Agent",
    description="AI agent that fills cancelled appointment slots",
)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Agent State ---
# In-memory state for the running agent loop
# (In production, this would be in a database or Redis)

agent_state = {
    "candidates": [],
    "current_index": 0,
    "action_start_time": None,
    "is_running": False,
}


# --- Pydantic Models ---

class CallOutcome(BaseModel):
    """Webhook payload from Bland.ai when a call ends."""
    patient_name: str
    outcome: str  # "confirmed", "declined", "no_answer"


class SMSReply(BaseModel):
    """Webhook payload from Twilio when SMS reply received."""
    patient_name: str
    reply: str  # The actual text message


# --- Lifecycle ---

@app.on_event("startup")
async def startup():
    """Initialize Firebase on startup."""
    # Try to get service account path from env, otherwise use default location
    service_account_path = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "serviceAccountKey.json"
    )

    # Only initialize if the file exists
    if os.path.exists(service_account_path):
        init_firestore(service_account_path)
        print(f"Firebase initialized with {service_account_path}")
    else:
        print(f"WARNING: {service_account_path} not found. Firebase not initialized.")
        print("Set GOOGLE_APPLICATION_CREDENTIALS or place serviceAccountKey.json in project root.")


# --- Endpoints ---

@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "agent_running": agent_state["is_running"]}


@app.post("/cancellation")
async def trigger_cancellation(background_tasks: BackgroundTasks):
    """
    Trigger the agent to start filling a cancelled slot.

    Called by the UI when "Trigger Cancellation" button is clicked,
    or by backend when a real cancellation is detected.
    """
    if agent_state["is_running"]:
        return {"status": "already_running"}

    background_tasks.add_task(run_agent_loop)
    return {"status": "agent_started"}


@app.post("/call-outcome")
async def call_outcome(body: CallOutcome):
    """
    Receive call outcome from Bland.ai webhook.

    Bland.ai calls this when a voice call ends.
    """
    if not agent_state["is_running"]:
        return {"status": "agent_not_running"}

    idx = agent_state["current_index"]
    candidates = agent_state["candidates"]

    if idx >= len(candidates):
        return {"status": "invalid_index"}

    # Map outcome to status
    status_map = {
        "confirmed": "confirmed",
        "declined": "declined",
        "no_answer": "no_answer",
    }
    new_status = status_map.get(body.outcome, "no_answer")

    # Update candidate status
    agent_state["candidates"] = update_candidate_status(candidates, idx, new_status)
    update_candidates(agent_state["candidates"])

    # Reset action timer for next decision
    agent_state["action_start_time"] = time.time()

    # Log the outcome
    patient_name = candidates[idx]["name"]
    add_activity("call_outcome", f"{patient_name}: {body.outcome}")

    return {"status": "received", "patient": patient_name, "outcome": body.outcome}


@app.post("/sms-reply")
async def sms_reply(body: SMSReply):
    """
    Receive SMS reply from Twilio webhook.

    Twilio calls this when a patient replies to our SMS.
    """
    if not agent_state["is_running"]:
        return {"status": "agent_not_running"}

    idx = agent_state["current_index"]
    candidates = agent_state["candidates"]

    if idx >= len(candidates):
        return {"status": "invalid_index"}

    # Parse reply - look for yes/no
    reply_lower = body.reply.lower().strip()
    if reply_lower in ("yes", "y", "yeah", "sure", "ok", "okay"):
        new_status = "confirmed"
    elif reply_lower in ("no", "n", "nope", "can't", "cannot"):
        new_status = "declined"
    else:
        # Ambiguous reply - treat as declined for demo simplicity
        new_status = "declined"

    # Update candidate status
    agent_state["candidates"] = update_candidate_status(candidates, idx, new_status)
    update_candidates(agent_state["candidates"])

    # Reset action timer
    agent_state["action_start_time"] = time.time()

    # Log the reply
    patient_name = candidates[idx]["name"]
    add_activity("call_outcome", f"{patient_name} replied: '{body.reply}' → {new_status}")

    return {"status": "received", "patient": patient_name, "outcome": new_status}


@app.post("/reset")
async def reset_demo():
    """
    Reset the demo to initial state.

    Called by UI "Reset Demo" button.
    """
    agent_state["candidates"] = []
    agent_state["current_index"] = 0
    agent_state["action_start_time"] = None
    agent_state["is_running"] = False

    reset_session()

    return {"status": "reset_complete"}


# --- Agent Loop ---

async def run_agent_loop():
    """
    Main agent loop. Runs in background after /cancellation is called.

    This is the "body" that uses the brain's decision logic.
    """
    agent_state["is_running"] = True

    try:
        # Step 1: Update status to running
        update_agent_status("running")
        update_slot_status("filling")
        add_activity("event", "Cancellation received — agent starting")

        # Step 2: Score candidates
        add_activity("thinking", f"Scoring {len(RECALL_LIST)} candidates from recall list...")
        await asyncio.sleep(1)  # Dramatic pause for demo

        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)
        agent_state["candidates"] = candidates
        agent_state["current_index"] = 0
        agent_state["action_start_time"] = time.time()
        update_candidates(candidates)

        add_activity("thinking", f"Top candidate: {candidates[0]['name']} (score: {candidates[0]['score']})")
        await asyncio.sleep(0.5)

        # Step 3: Main decision loop
        while True:
            elapsed = time.time() - agent_state["action_start_time"]

            action, idx = get_next_action(
                agent_state["candidates"],
                agent_state["current_index"],
                elapsed
            )
            agent_state["current_index"] = idx

            # Handle each action type
            if action == "done":
                # SUCCESS - slot filled!
                patient = agent_state["candidates"][idx]
                update_slot_status("filled", filled_by=patient["name"])
                update_recovered(DEMO_SLOT["value"])
                update_agent_status("complete")
                add_activity("success", f"Slot filled by {patient['name']}. Recovered ${DEMO_SLOT['value']}.")
                break

            elif action == "give_up":
                # FAILURE - all candidates exhausted
                update_slot_status("exhausted")
                update_agent_status("failed")
                add_activity("error", "All candidates exhausted — slot unfilled")
                break

            elif action == "call":
                patient = agent_state["candidates"][idx]

                # Update status to "calling"
                agent_state["candidates"] = update_candidate_status(
                    agent_state["candidates"], idx, "calling"
                )
                update_candidates(agent_state["candidates"])

                # Log and trigger call
                add_activity("tool_call", f"Calling {patient['name']} ({patient['phone']})...")
                agent_state["action_start_time"] = time.time()

                # VOICE GUY IMPLEMENTS THIS
                trigger_voice_call(patient)

            elif action == "sms":
                patient = agent_state["candidates"][idx]

                # Update status to "texting"
                agent_state["candidates"] = update_candidate_status(
                    agent_state["candidates"], idx, "texting"
                )
                update_candidates(agent_state["candidates"])

                # Log and send SMS
                add_activity("sms_sent", f"SMS sent to {patient['name']}")
                agent_state["action_start_time"] = time.time()

                # VOICE GUY IMPLEMENTS THIS
                send_sms(patient, DEMO_SLOT)

            elif action == "next_candidate":
                patient = agent_state["candidates"][idx]
                add_activity("thinking", f"Moving to next candidate: {patient['name']}")
                agent_state["action_start_time"] = time.time()

            elif action == "wait":
                # Still waiting for webhook response
                pass

            # Small delay to prevent tight loop
            await asyncio.sleep(1)

    finally:
        agent_state["is_running"] = False


# --- Voice/SMS Stubs (VOICE GUY OWNS THESE) ---

def trigger_voice_call(patient: dict):
    """
    Trigger a voice call via Bland.ai.

    VOICE GUY IMPLEMENTS THIS.

    Should call Bland.ai API to initiate a call.
    When call ends, Bland.ai will POST to /call-outcome with the result.

    Args:
        patient: Dict with "name" and "phone" keys
    """
    # TODO: Voice guy implements Bland.ai integration
    # Example:
    # response = requests.post("https://api.bland.ai/v1/calls", json={
    #     "phone_number": patient["phone"],
    #     "task": f"Call {patient['name']} about the 2 PM cleaning appointment...",
    #     "webhook": "https://your-server.com/call-outcome"
    # }, headers={"Authorization": f"Bearer {BLAND_API_KEY}"})
    print(f"[STUB] Would call {patient['name']} at {patient['phone']}")


def send_sms(patient: dict, slot: dict):
    """
    Send an SMS via Twilio.

    VOICE GUY IMPLEMENTS THIS.

    Should call Twilio API to send an SMS.
    When patient replies, Twilio will POST to /sms-reply with the response.

    Args:
        patient: Dict with "name" and "phone" keys
        slot: Dict with appointment details
    """
    # TODO: Voice guy implements Twilio integration
    # Example:
    # client = twilio.Client(TWILIO_SID, TWILIO_TOKEN)
    # client.messages.create(
    #     body=f"Hi {patient['name']}, we have an opening at {slot['time']} for a {slot['treatment']}. Reply YES to book.",
    #     from_=TWILIO_PHONE,
    #     to=patient["phone"]
    # )
    print(f"[STUB] Would SMS {patient['name']} at {patient['phone']}")


# --- Run directly ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
