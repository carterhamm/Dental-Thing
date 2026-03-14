"""
Claude Agent orchestrator — Spencer's PM runtime.

Wraps Eddy's brain functions with Claude's reasoning via tool use.
Writes to Carter's Firestore schema so the dashboard updates in real-time.

The orchestrator is event-driven:
  1. main.py calls start() on cancellation → Claude ranks + initiates first outreach
  2. Webhook delivers outcome → main.py calls handle_outcome() → Claude decides next step
  3. Repeat until booked or exhausted
"""

import anthropic

from agent.brain import (
    score_candidates,
    get_next_action,
    update_candidate_status,
    calculate_recovered_revenue,
)
from agent.firestore import (
    add_activity,
    update_agent_status,
    update_slot_status,
    update_candidates,
    update_recovered,
    update_schedule_slot,
)
from agent.mock_data import RECALL_LIST


TOOLS = [
    {
        "name": "rank_candidates",
        "description": (
            "Score and rank waitlist candidates for the open slot. "
            "Call this first when a cancellation is detected."
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
            "Given current candidates and index, decide next action: "
            "call, sms, next_candidate, give_up, or done."
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
        "name": "initiate_voice_call",
        "description": (
            "Initiate a voice call to a candidate. Updates their status to 'calling' "
            "and signals the comms layer. The outcome will arrive asynchronously via webhook."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate_index": {
                    "type": "integer",
                    "description": "Index of the candidate to call",
                },
            },
            "required": ["candidate_index"],
        },
    },
    {
        "name": "initiate_sms",
        "description": (
            "Send an SMS to a candidate. Updates their status to 'texting' "
            "and signals the comms layer. The reply will arrive asynchronously via webhook."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate_index": {
                    "type": "integer",
                    "description": "Index of the candidate to text",
                },
            },
            "required": ["candidate_index"],
        },
    },
    {
        "name": "book_appointment",
        "description": "Finalize the booking when a candidate is confirmed.",
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
            "Log your reasoning to the activity feed. Judges see this in real-time. "
            "Be specific: mention scores, names, and why you chose this action."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Your reasoning (1-2 sentences)",
                },
            },
            "required": ["text"],
        },
    },
]

SYSTEM_PROMPT = """\
You are a dental scheduling AI agent for Bright Smile Dental. A patient just \
cancelled their appointment and you need to fill the slot by contacting \
candidates from the recall list.

Your workflow:
1. rank_candidates to score the waitlist, then IMMEDIATELY log_thinking to explain (batch both in one response).
2. decide_next_action to get the brain's recommendation.
3. Based on the action, BATCH log_thinking + the action tool in a single response:
   - "call" → log_thinking why + initiate_voice_call (BOTH in one response)
   - "sms" → log_thinking fallback reason + initiate_sms (BOTH in one response)
   - "next_candidate" → log_thinking why moving on + decide_next_action with new index (BOTH in one response)
   - "done" → log_thinking to celebrate + book_appointment (BOTH in one response)
   - "give_up" → log_thinking summarizing, then stop
4. After initiating a call or SMS, STOP and return. The outcome arrives via webhook.

CRITICAL RULES:
- ALWAYS use parallel/batched tool calls to minimize round trips. Call multiple tools in ONE response.
- ALWAYS log_thinking before taking action — the feed IS the demo.
- Be specific: "Sarah Kim scores 82 — 15 days overdue, exact treatment match, 90% reliable."
- Keep reasoning to 1-2 sentences. Sound like a smart assistant, not a robot.
- After initiating a call or SMS, you MUST stop. Do not loop.
- NEVER call book_appointment unless you received an explicit "confirmed" outcome. \
If the outcome was "no_answer" or "declined", move to the next candidate or try SMS.
"""


class Orchestrator:
    """Manages the Claude agent loop and candidate state."""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.candidates: list[dict] = []
        self.slot: dict = {}
        self.current_index: int = -1
        self.cancelled: bool = False  # Set by reset to stop run_step loop
        # Comms callbacks — main.py wires these to real Twilio/ElevenLabs
        self.on_voice_call: callable = None
        self.on_sms: callable = None

    def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool call and return the result string."""

        if tool_name == "rank_candidates":
            self.slot = tool_input["slot"]
            self.candidates = score_candidates(RECALL_LIST, self.slot)
            update_candidates(self.candidates)
            add_activity(
                "event",
                f"Ranked {len(self.candidates)} candidates for "
                f"{self.slot['time']} {self.slot['treatment']}",
            )
            summary = ", ".join(
                f"#{c['rank']} {c['name']} (score: {c['score']})"
                for c in self.candidates
            )
            return f"Ranked {len(self.candidates)} candidates: {summary}"

        elif tool_name == "decide_next_action":
            idx = tool_input["current_candidate_index"]
            action, candidate_idx = get_next_action(self.candidates, idx)
            self.current_index = candidate_idx
            result = {"action": action, "candidate_index": candidate_idx}
            if action in ("call", "sms", "next_candidate", "done") and 0 <= candidate_idx < len(self.candidates):
                result["candidate_name"] = self.candidates[candidate_idx]["name"]
            return str(result)

        elif tool_name == "initiate_voice_call":
            idx = tool_input["candidate_index"]
            candidate = self.candidates[idx]
            self.candidates = update_candidate_status(self.candidates, idx, "calling")
            self.current_index = idx
            update_candidates(self.candidates)
            add_activity("tool_call", f"Calling {candidate['name']} ({candidate['phone']})...")
            if self.on_voice_call:
                self.on_voice_call(candidate)
            return f"Voice call initiated to {candidate['name']}. Waiting for outcome via webhook."

        elif tool_name == "initiate_sms":
            idx = tool_input["candidate_index"]
            candidate = self.candidates[idx]
            self.candidates = update_candidate_status(self.candidates, idx, "texting")
            self.current_index = idx
            update_candidates(self.candidates)
            add_activity("sms_sent", f"SMS sent to {candidate['name']} ({candidate['phone']})")
            if self.on_sms:
                self.on_sms(candidate, self.slot)
            return f"SMS sent to {candidate['name']}. Waiting for reply via webhook."

        elif tool_name == "book_appointment":
            idx = tool_input["candidate_index"]
            candidate = self.candidates[idx]
            # Safety check: only book if the candidate actually confirmed
            if candidate["status"] != "confirmed":
                return (
                    f"CANNOT book {candidate['name']} — their status is '{candidate['status']}', not 'confirmed'. "
                    f"Call decide_next_action to determine the correct next step."
                )
            revenue = calculate_recovered_revenue(self.slot)
            update_slot_status("filled", filled_by=candidate["name"])
            update_recovered(revenue)
            update_agent_status("complete")
            # Update the daily schedule view
            slot_id = self.slot.get("id", "slot_1400")
            update_schedule_slot(slot_id, candidate["name"])
            add_activity("success", f"Slot filled by {candidate['name']}! Recovered ${revenue}.")
            return f"Booked! {candidate['name']} confirmed. ${revenue} recovered."

        elif tool_name == "log_thinking":
            add_activity("thinking", tool_input["text"])
            return "Logged."

        return f"Unknown tool: {tool_name}"

    def run_step(self, user_message: str) -> str:
        """Run one step of the Claude agent loop."""
        if self.cancelled:
            return ""

        messages = [{"role": "user", "content": user_message}]

        for _ in range(15):
            if self.cancelled:
                return ""

            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                text_parts = [b.text for b in response.content if hasattr(b, "text")]
                return " ".join(text_parts) if text_parts else ""

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self.execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            if not tool_results:
                break

            messages.append({"role": "user", "content": tool_results})

        return ""

    def start(self, slot: dict) -> str:
        """Start the agent for a cancelled slot.

        FAST PATH: Ranks candidates and initiates the first call immediately
        using the deterministic brain logic — no Claude API calls needed.
        Claude is only invoked later when an outcome arrives.
        """
        self.slot = slot
        self.candidates = []
        self.current_index = -1

        update_agent_status("running")
        update_slot_status("filling")
        add_activity("event", f"Cancellation detected — {slot['time']} {slot['treatment']} (${slot['value']})")

        # Score candidates instantly (deterministic brain logic, no API call)
        self.candidates = score_candidates(RECALL_LIST, slot)
        update_candidates(self.candidates)
        add_activity("event", f"Ranked {len(self.candidates)} candidates for {slot['time']} {slot['treatment']}")

        # Log top 3 for the dashboard
        top = self.candidates[:3]
        top_summary = "; ".join(
            f"#{c['rank']} {c['name']} (score {c['score']})" for c in top
        )
        add_activity("thinking", f"Top candidates: {top_summary}")

        # Get first action from brain (always "call", 0 for a fresh list)
        action, candidate_idx = get_next_action(self.candidates, -1)
        self.current_index = candidate_idx

        if action == "call" and 0 <= candidate_idx < len(self.candidates):
            candidate = self.candidates[candidate_idx]
            self.candidates = update_candidate_status(
                self.candidates, candidate_idx, "calling"
            )
            update_candidates(self.candidates)
            add_activity(
                "thinking",
                f"Calling {candidate['name']} first — highest score, best match for this slot.",
            )
            add_activity(
                "tool_call",
                f"Calling {candidate['name']} ({candidate['phone']})...",
            )
            if self.on_voice_call:
                self.on_voice_call(candidate)
            return f"Voice call initiated to {candidate['name']}. Waiting for outcome."

        # Fallback for edge cases (empty list, etc.) — let Claude handle it
        return self.run_step(
            f"A patient cancelled their {slot['treatment']} appointment at {slot['time']}. "
            f"Slot value: ${slot['value']}. Date: {slot['date']}. "
            f"Candidates already ranked. Decide next action."
        )

    def handle_outcome(self, candidate_name: str, outcome: str) -> str:
        """Handle a webhook outcome. Re-invokes Claude to decide next steps."""
        if self.cancelled:
            return ""

        # First, try to use current_index if it matches the name (avoids duplicate name issues)
        matched_index = None
        if 0 <= self.current_index < len(self.candidates):
            if self.candidates[self.current_index]["name"] == candidate_name:
                matched_index = self.current_index

        # Fall back to searching by name if current_index doesn't match
        if matched_index is None:
            for i, c in enumerate(self.candidates):
                if c["name"] == candidate_name:
                    matched_index = i
                    break

        if matched_index is not None:
            self.candidates = update_candidate_status(self.candidates, matched_index, outcome)
            self.current_index = matched_index
            update_candidates(self.candidates)

        outcome_label = {
            "confirmed": "confirmed",
            "declined": "declined",
            "no_answer": "no answer",
            "no_reply": "no reply",
        }.get(outcome, outcome)
        add_activity("call_outcome", f"{candidate_name}: {outcome_label}")

        if outcome == "confirmed":
            return self.run_step(f"{candidate_name} confirmed! Book the appointment.")
        elif outcome == "declined":
            return self.run_step(
                f"{candidate_name} DECLINED the appointment. DO NOT book them. "
                f"Move to the next candidate. Call decide_next_action with index {self.current_index}."
            )
        else:
            return self.run_step(
                f"Outcome for {candidate_name}: {outcome_label}. "
                f"Current index: {self.current_index}. "
                f"Call decide_next_action to determine the next step."
            )

    def give_up(self) -> None:
        """Mark the campaign as failed."""
        update_slot_status("exhausted")
        update_agent_status("failed")
        add_activity("error", "All candidates exhausted — slot unfilled.")
