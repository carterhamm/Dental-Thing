"""
Claude Agent SDK orchestrator — the PM's core runtime.

This is the AI agent that decides what to do when a slot is cancelled.
It calls Eddy's brain.py for scoring/decisions and writes outreach intents
to Firestore for the UI/Voice layer to execute.

The agent uses Claude's tool-use to drive a loop:
  rank → pick candidate → request outreach → wait for outcome → next step
"""

import time
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY
from brain import (
    score_candidates,
    get_next_action,
    update_candidate_status,
    calculate_recovered_revenue,
    RECALL_LIST,
)
from firestore_client import (
    log_activity,
    set_agent_status,
    set_slot_status,
    update_candidates,
    write_pending_action,
    read_and_clear_pending_outcome,
    book_slot,
)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ---------------------------------------------------------------------------
# Tool definitions for Claude
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "name": "rank_candidates",
        "description": (
            "Score and rank waitlist candidates for the open slot. "
            "Call this first when a cancellation is detected. "
            "Returns a ranked list with scores and reasoning."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "slot": {
                    "type": "object",
                    "description": "The cancelled slot to fill",
                    "properties": {
                        "treatment": {"type": "string"},
                        "time": {"type": "string"},
                        "date": {"type": "string"},
                        "value": {"type": "integer"},
                    },
                    "required": ["treatment", "time", "date", "value"],
                },
            },
            "required": ["slot"],
        },
    },
    {
        "name": "decide_next_action",
        "description": (
            "Given current candidates and which one we're working on, "
            "decide the next action: call, sms, next_candidate, give_up, or done."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "current_candidate_index": {
                    "type": "integer",
                    "description": "Index of current candidate (-1 if starting fresh)",
                },
            },
            "required": ["current_candidate_index"],
        },
    },
    {
        "name": "request_voice_call",
        "description": (
            "Request a voice call to a candidate. Writes intent to Firestore, "
            "UI/Voice layer executes via ElevenLabs+Twilio. "
            "Blocks until the call outcome is available (up to 60s)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate_index": {
                    "type": "integer",
                    "description": "Index of the candidate to call",
                },
                "message": {
                    "type": "string",
                    "description": "What to say on the call (context for the voice agent)",
                },
            },
            "required": ["candidate_index", "message"],
        },
    },
    {
        "name": "request_sms",
        "description": (
            "Send an SMS to a candidate. Writes intent to Firestore, "
            "UI/Voice layer sends via Twilio. "
            "Blocks until a reply or timeout (up to 60s)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate_index": {
                    "type": "integer",
                    "description": "Index of the candidate to text",
                },
                "message": {
                    "type": "string",
                    "description": "SMS body to send",
                },
            },
            "required": ["candidate_index", "message"],
        },
    },
    {
        "name": "update_candidate",
        "description": "Update a candidate's status after an outreach outcome.",
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate_index": {
                    "type": "integer",
                    "description": "Index of the candidate to update",
                },
                "new_status": {
                    "type": "string",
                    "enum": [
                        "waiting", "calling", "texting",
                        "declined", "no_answer", "confirmed",
                    ],
                    "description": "New status for this candidate",
                },
            },
            "required": ["candidate_index", "new_status"],
        },
    },
    {
        "name": "book_appointment",
        "description": (
            "Finalize booking when a candidate confirms. "
            "Marks the slot as filled and records recovered revenue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate_index": {
                    "type": "integer",
                    "description": "Index of the confirmed candidate",
                },
            },
            "required": ["candidate_index"],
        },
    },
    {
        "name": "log_thinking",
        "description": (
            "Log agent reasoning to the activity feed. "
            "Judges see this — make it clear, concise, and show your logic."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Reasoning text to display in the activity feed",
                },
            },
            "required": ["text"],
        },
    },
]

SYSTEM_PROMPT = """\
You are a dental scheduling AI agent for Bright Smile Dental. A patient just \
cancelled their appointment and you need to fill the slot by contacting \
candidates from the recall/waitlist.

Your workflow:
1. Call rank_candidates to score and rank the waitlist for this slot.
2. Call decide_next_action to determine your next move.
3. Based on the action:
   - "call" → Use log_thinking to explain why this candidate, then request_voice_call
   - "sms" → Use log_thinking to explain the fallback, then request_sms
   - "next_candidate" → Use log_thinking to explain why you're moving on, then decide_next_action again
   - "done" → A candidate confirmed! Call book_appointment.
   - "give_up" → All candidates exhausted. Log it and stop.
4. After each outreach result, call update_candidate with the outcome.
5. Loop back to decide_next_action.

Guidelines:
- Always log_thinking before taking action — the activity feed IS the demo.
- Be specific: "Sarah Kim scores 82/100 — 15 days overdue, exact treatment match, 90% reliability."
- Keep reasoning to 1-2 sentences. Sound like a smart assistant, not a robot.
- When a candidate confirms, celebrate briefly in the log before booking.
- If all candidates are exhausted, log a clear summary of what happened.
"""


# ---------------------------------------------------------------------------
# Tool execution — maps Claude's tool calls to actual logic
# ---------------------------------------------------------------------------

# Module-level state for the current agent run
_candidates: list[dict] = []
_slot: dict = {}


def _poll_for_outcome(timeout_seconds: int = 60, interval: float = 2.0) -> dict:
    """Poll Firestore for pending_outcome from UI/Voice layer."""
    elapsed = 0.0
    while elapsed < timeout_seconds:
        outcome = read_and_clear_pending_outcome()
        if outcome is not None:
            return outcome
        time.sleep(interval)
        elapsed += interval
    return {"type": "unknown", "result": "no_answer", "details": "Timeout — no response"}


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result as a string for Claude."""
    global _candidates, _slot

    if tool_name == "rank_candidates":
        slot = tool_input["slot"]
        _slot = slot
        _candidates = score_candidates(RECALL_LIST, slot)
        update_candidates(_candidates)
        log_activity("event", f"Ranked {len(_candidates)} candidates for {slot['time']} {slot['treatment']}")
        return f"Ranked {len(_candidates)} candidates: " + ", ".join(
            f"#{c['rank']} {c['name']} (score: {c['score']})" for c in _candidates
        )

    elif tool_name == "decide_next_action":
        idx = tool_input["current_candidate_index"]
        action, candidate_idx = get_next_action(_candidates, idx)
        if action in ("call", "sms") and 0 <= candidate_idx < len(_candidates):
            name = _candidates[candidate_idx]["name"]
            return f'{{"action": "{action}", "candidate_index": {candidate_idx}, "candidate_name": "{name}"}}'
        return f'{{"action": "{action}", "candidate_index": {candidate_idx}}}'

    elif tool_name == "request_voice_call":
        idx = tool_input["candidate_index"]
        candidate = _candidates[idx]
        _candidates = update_candidate_status(_candidates, idx, "calling")
        update_candidates(_candidates)
        log_activity("tool_call", f"Calling {candidate['name']} ({candidate['phone']})...")
        write_pending_action("voice", candidate["phone"], candidate["name"], tool_input["message"])
        outcome = _poll_for_outcome()
        result = outcome.get("result", "no_answer")
        details = outcome.get("details", "")
        log_activity("call_outcome", f"Call to {candidate['name']}: {result}. {details}".strip())
        return f'{{"result": "{result}", "details": "{details}"}}'

    elif tool_name == "request_sms":
        idx = tool_input["candidate_index"]
        candidate = _candidates[idx]
        _candidates = update_candidate_status(_candidates, idx, "texting")
        update_candidates(_candidates)
        log_activity("sms_sent", f"SMS sent to {candidate['name']} ({candidate['phone']})")
        write_pending_action("sms", candidate["phone"], candidate["name"], tool_input["message"])
        outcome = _poll_for_outcome()
        result = outcome.get("result", "no_answer")
        details = outcome.get("details", "")
        log_activity(
            "call_outcome" if result == "no_answer" else "event",
            f"SMS to {candidate['name']}: {result}. {details}".strip(),
        )
        return f'{{"result": "{result}", "details": "{details}"}}'

    elif tool_name == "update_candidate":
        idx = tool_input["candidate_index"]
        new_status = tool_input["new_status"]
        _candidates = update_candidate_status(_candidates, idx, new_status)
        update_candidates(_candidates)
        return f"Updated {_candidates[idx]['name']} to {new_status}"

    elif tool_name == "book_appointment":
        idx = tool_input["candidate_index"]
        candidate = _candidates[idx]
        _candidates = update_candidate_status(_candidates, idx, "confirmed")
        update_candidates(_candidates)
        revenue = calculate_recovered_revenue(_slot)
        book_slot(candidate["name"], revenue)
        log_activity("success", f"Slot filled by {candidate['name']}! Recovered ${revenue}.")
        return f"Booked! {candidate['name']} confirmed for {_slot['time']}. ${revenue} recovered."

    elif tool_name == "log_thinking":
        log_activity("thinking", tool_input["text"])
        return "Logged."

    else:
        return f"Unknown tool: {tool_name}"


# ---------------------------------------------------------------------------
# Agent loop — drives the Claude conversation with tool use
# ---------------------------------------------------------------------------

def run_agent(slot: dict) -> dict:
    """Run the full agent loop for a cancelled slot.

    This is the main entry point. Call it when a cancellation is detected.
    Returns {"status": "filled", "by": name} or {"status": "failed"}.
    """
    global _candidates, _slot
    _candidates = []
    _slot = slot

    set_agent_status("running")
    set_slot_status("filling")
    log_activity("event", f"Cancellation detected — {slot['time']} {slot['treatment']} (${slot['value']})")

    messages = [
        {
            "role": "user",
            "content": (
                f"A patient just cancelled their {slot['treatment']} appointment at {slot['time']}. "
                f"Slot value: ${slot['value']}. Date: {slot['date']}. "
                f"Fill this slot. Start by ranking candidates, then work through them."
            ),
        }
    ]

    # Agentic loop — keep going until the agent stops calling tools
    max_turns = 30  # safety valve
    for _ in range(max_turns):
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Collect assistant message
        assistant_message = {"role": "assistant", "content": response.content}
        messages.append(assistant_message)

        # If the model stopped without tool use, we're done
        if response.stop_reason == "end_turn":
            break

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result_str = execute_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    }
                )

        if not tool_results:
            break

        messages.append({"role": "user", "content": tool_results})

    # Determine final state
    session = None
    try:
        from firestore_client import get_session
        session = get_session()
    except Exception:
        pass

    if session and session.get("slot", {}).get("status") == "filled":
        return {"status": "filled", "by": session["slot"].get("filled_by")}
    else:
        set_agent_status("failed")
        set_slot_status("exhausted")
        log_activity("error", "Could not fill slot — all candidates exhausted.")
        return {"status": "failed"}
