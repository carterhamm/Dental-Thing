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
)
from agent.firestore import (
    add_activity,
    update_agent_status,
    update_agent_phase,
    update_slot,
    update_patient,
    get_queued_patients,
    increment_attempt,
)
from agent.mock_data import RECALL_LIST


TOOLS = [
    {
        "name": "rank_candidates",
        "description": "Score and rank waitlist candidates for the open slot. Call this first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "slot": {
                    "type": "object",
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
        "description": "Given current candidates and index, decide: call, sms, next_candidate, give_up, or done.",
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
        "description": "Call a candidate. Outcome arrives via webhook — stop after this.",
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate_index": {"type": "integer"},
            },
            "required": ["candidate_index"],
        },
    },
    {
        "name": "initiate_sms",
        "description": "Text a candidate. Reply arrives via webhook — stop after this.",
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate_index": {"type": "integer"},
            },
            "required": ["candidate_index"],
        },
    },
    {
        "name": "book_appointment",
        "description": "Finalize the booking when a candidate confirmed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate_index": {"type": "integer"},
            },
            "required": ["candidate_index"],
        },
    },
    {
        "name": "log_thinking",
        "description": "Log reasoning to the activity feed. Judges see this. Be specific with scores and names.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
            },
            "required": ["text"],
        },
    },
]

SYSTEM_PROMPT = """\
You are a dental scheduling AI agent for Bright Smile Dental. A patient just \
cancelled and you need to fill the slot by contacting candidates.

Workflow:
1. rank_candidates to score the waitlist.
2. log_thinking to explain your rankings.
3. decide_next_action to get the recommendation.
4. Based on action:
   - "call" → log_thinking why, then initiate_voice_call
   - "sms" → log_thinking the fallback, then initiate_sms
   - "next_candidate" → log_thinking why moving on, then decide_next_action with new index
   - "done" → celebrate briefly, then book_appointment
   - "give_up" → summarize what happened, then stop
5. After initiating a call or SMS, STOP. The outcome arrives via webhook.

Rules:
- ALWAYS log_thinking before acting. Be specific: names, scores, reasons.
- 1-2 sentences per log. Sound like a smart assistant.
- After initiate_voice_call or initiate_sms, you MUST stop and return.
"""


class Orchestrator:
    """Claude agent that drives the rescheduling flow."""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.candidates: list[dict] = []
        self.slot: dict = {}
        self.current_index: int = -1
        self.patient_ids: list[str] = []  # Firestore doc IDs (p0, p1, ...)
        # Comms callbacks — main.py wires these to real Twilio/ElevenLabs
        self.on_voice_call: callable = None
        self.on_sms: callable = None

    def _update_patient_status(self, idx: int, status: str) -> None:
        """Update both in-memory candidates and Firestore patient doc."""
        self.candidates = update_candidate_status(self.candidates, idx, status)
        if idx < len(self.patient_ids):
            # Map brain status to Carter's frontend status
            fe_status_map = {
                "calling": "calling",
                "no_answer": "no_answer",
                "texting": "sms_sent",
                "no_reply": "skipped",
                "declined": "skipped",
                "confirmed": "confirmed",
                "waiting": "queued",
            }
            fe_status = fe_status_map.get(status, status)
            update_patient(self.patient_ids[idx], fe_status)

    def execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Execute a tool call from Claude."""

        if tool_name == "rank_candidates":
            self.slot = tool_input["slot"]
            self.candidates = score_candidates(RECALL_LIST, self.slot)

            # Map candidates to Firestore patient doc IDs
            patients = get_queued_patients()
            self.patient_ids = []
            for c in self.candidates:
                matched = next((p for p in patients if p["name"] == c["name"]), None)
                self.patient_ids.append(matched["id"] if matched else f"p{len(self.patient_ids)}")

            add_activity(
                "🔍",
                f"Ranked {len(self.candidates)} candidates for {self.slot['time']} {self.slot.get('treatment', 'cleaning')}",
                "system",
            )
            summary = ", ".join(
                f"#{c['rank']} {c['name']} (score: {c['score']})" for c in self.candidates
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
            self._update_patient_status(idx, "calling")
            self.current_index = idx
            increment_attempt()
            update_agent_phase("calling", candidate["name"])
            add_activity("📞", f"Calling {candidate['name']}...", "call")
            if self.on_voice_call:
                self.on_voice_call(candidate)
            return f"Voice call initiated to {candidate['name']}. Waiting for outcome."

        elif tool_name == "initiate_sms":
            idx = tool_input["candidate_index"]
            candidate = self.candidates[idx]
            self._update_patient_status(idx, "texting")
            self.current_index = idx
            update_agent_phase("sms_sent", candidate["name"])
            add_activity(
                "💬",
                f"SMS sent to {candidate['name']}: \"Hi {candidate['name']}, we have an opening at "
                f"{self.slot.get('time', '2:30 PM')} for a cleaning. Would you like to book it?\"",
                "sms",
            )
            if self.on_sms:
                self.on_sms(candidate, self.slot)
            return f"SMS sent to {candidate['name']}. Waiting for reply."

        elif tool_name == "book_appointment":
            idx = tool_input["candidate_index"]
            candidate = self.candidates[idx]
            self._update_patient_status(idx, "confirmed")
            update_agent_phase("booking", candidate["name"])
            update_slot("booking")
            add_activity("📋", "Confirming appointment...", "system")
            # Small delay would be nice here but we're sync — main.py handles the finalize
            update_agent_phase("filled", candidate["name"])
            update_slot("filled", booked_by=candidate["name"])
            add_activity("✅", f"Slot filled! {candidate['name']} booked for {self.slot.get('time', '2:30 PM')}", "success")
            return f"Booked! {candidate['name']} confirmed."

        elif tool_name == "log_thinking":
            add_activity("🧠", tool_input["text"], "system")
            return "Logged."

        return f"Unknown tool: {tool_name}"

    def run_step(self, user_message: str) -> str:
        """Run one step of Claude reasoning. Returns after outreach is initiated or decision is final."""
        messages = [{"role": "user", "content": user_message}]

        for _ in range(15):
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
        """Start the agent for a cancelled slot."""
        self.slot = slot
        self.candidates = []
        self.current_index = -1

        total = len(get_queued_patients())
        update_agent_status("calling", attempt=0, total_patients=total)
        add_activity("⚠️", f"Cancellation received — starting outreach for {slot.get('time', '2:30 PM')} slot", "warning")

        return self.run_step(
            f"A patient cancelled their cleaning appointment at {slot.get('time', '2:30 PM')}. "
            f"Slot value: ${slot.get('value', 185)}. Date: today. "
            f"Fill this slot. Rank candidates, explain your reasoning, then start contacting."
        )

    def handle_outcome(self, patient_name: str, outcome: str) -> str:
        """Handle a comms outcome (call result or SMS reply). Re-invokes Claude."""
        # Update the candidate
        for i, c in enumerate(self.candidates):
            if c["name"] == patient_name:
                self._update_patient_status(i, outcome)
                self.current_index = i
                break

        # Update dashboard
        outcome_map = {
            "confirmed": ("sms_reply", "💬", f'{patient_name}: "Yes, that works!"', "success"),
            "declined": ("no_answer", "📞", f"{patient_name} declined", "warning"),
            "no_answer": ("no_answer", "📞", f"{patient_name} — no answer", "warning"),
            "no_reply": ("no_answer", "💬", f"{patient_name} — no reply", "warning"),
        }
        phase, icon, msg, log_type = outcome_map.get(
            outcome, ("no_answer", "📞", f"{patient_name}: {outcome}", "warning")
        )
        update_agent_phase(phase, patient_name)
        add_activity(icon, msg, log_type)

        if outcome == "confirmed":
            return self.run_step(f"{patient_name} confirmed! Book the appointment.")
        else:
            return self.run_step(
                f"Outcome for {patient_name}: {outcome}. "
                f"Current candidates: {self.candidates}. "
                f"Current index: {self.current_index}. Decide what to do next."
            )

    def give_up(self) -> None:
        """All candidates exhausted."""
        update_agent_phase("idle")
        update_slot("open")
        add_activity("❌", "All patients contacted — slot unfilled", "warning")
