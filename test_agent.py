#!/usr/bin/env python3
"""
CLI test harness for the dental rescheduling agent.

Runs the agent end-to-end with no infrastructure — no Firebase, no Twilio,
no FastAPI server. Just the Claude orchestrator + your text input.

Usage:
    # Interactive mode — you play the patient
    python test_agent.py

    # Auto mode — preset scenario plays out
    python test_agent.py --auto
    python test_agent.py --auto --scenario tough

    # Pick a different slot type
    python test_agent.py --slot filling
    python test_agent.py --slot crown --auto
"""

import os
import sys
import threading

from dotenv import load_dotenv

load_dotenv()

from agent.mock_data import DEMO_SLOT, DEMO_SLOTS
from orchestrator import Orchestrator


# ---------------------------------------------------------------------------
# Preset scenarios for --auto mode
# ---------------------------------------------------------------------------

SCENARIOS = {
    "default":     ["no_answer", "confirmed"],
    "tough":       ["no_answer", "declined", "no_answer", "declined", "confirmed"],
    "all_decline": ["declined", "declined", "declined", "declined", "declined",
                    "declined", "declined", "declined", "declined", "declined"],
    "first_try":   ["confirmed"],
    "sms_save":    ["no_answer", "no_answer", "confirmed"],
}


def print_banner(slot: dict, mode: str):
    print()
    print("=" * 60)
    print("  DENTAL RESCHEDULING AGENT — TEST HARNESS")
    print("=" * 60)
    print(f"  Slot:  {slot['treatment']} at {slot['time']} (${slot['value']})")
    print(f"  Mode:  {mode}")
    print("=" * 60)
    print()


def run_interactive(slot: dict):
    """Interactive mode — you type patient responses."""

    print_banner(slot, "interactive — you play the patient")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in .env or environment")
        sys.exit(1)

    orch = Orchestrator(api_key)

    # When the agent initiates a call or SMS, we intercept it and prompt for input
    pending_outcome = threading.Event()
    pending_patient = {"name": "", "channel": ""}

    def on_call(patient):
        pending_patient["name"] = patient["name"]
        pending_patient["channel"] = "call"
        pending_outcome.set()

    def on_sms(patient, slot_info):
        pending_patient["name"] = patient["name"]
        pending_patient["channel"] = "sms"
        pending_outcome.set()

    orch.on_voice_call = on_call
    orch.on_sms = on_sms

    # Start the agent
    print("Starting agent...\n")
    orch.start(slot)

    # Loop: wait for outreach, get user input, feed outcome back
    while True:
        if not pending_outcome.is_set():
            # Agent finished without initiating outreach — it's done
            break

        pending_outcome.clear()
        name = pending_patient["name"]
        channel = pending_patient["channel"]

        print()
        print("-" * 40)
        if channel == "call":
            print(f"INCOMING CALL to {name}")
            print("How does the patient respond?")
        else:
            print(f"SMS SENT to {name}")
            print(f'  "Hi {name}, we had a cancellation at {slot["time"]} '
                  f'for a {slot["treatment"]}. Want to take it? Reply YES or NO."')
            print("How does the patient respond?")

        print()
        print("  [1] confirmed  — patient says yes")
        print("  [2] declined   — patient says no")
        print("  [3] no_answer  — no pickup / no reply")
        print()

        while True:
            choice = input("  > ").strip().lower()
            if choice in ("1", "confirmed", "yes", "y"):
                outcome = "confirmed"
                break
            elif choice in ("2", "declined", "no", "n"):
                outcome = "declined"
                break
            elif choice in ("3", "no_answer", "na", ""):
                outcome = "no_answer" if channel == "call" else "no_reply"
                break
            else:
                print("  Pick 1, 2, or 3")

        print(f"\n  → {name}: {outcome}\n")
        result = orch.handle_outcome(name, outcome)

        # Check if agent is done
        if orch.candidates:
            any_confirmed = any(c["status"] == "confirmed" for c in orch.candidates)
            all_terminal = all(
                c["status"] in ("declined", "no_answer", "no_reply", "confirmed")
                for c in orch.candidates
            )
            if any_confirmed or all_terminal:
                break

    print()
    print("=" * 60)
    print("  AGENT COMPLETE")
    print("=" * 60)

    # Summary
    if orch.candidates:
        confirmed = [c for c in orch.candidates if c["status"] == "confirmed"]
        if confirmed:
            winner = confirmed[0]
            print(f"  Slot filled by: {winner['name']}")
            print(f"  Revenue recovered: ${slot['value']}")
        else:
            print("  Slot unfilled — all candidates exhausted")

        contacted = [c for c in orch.candidates if c["status"] != "waiting"]
        print(f"  Candidates contacted: {len(contacted)}")
        for c in contacted:
            print(f"    {c['rank']}. {c['name']} — {c['status']}")
    print()


def run_auto(slot: dict, scenario_name: str):
    """Auto mode — preset outcomes, no user input."""

    scenario = SCENARIOS.get(scenario_name, SCENARIOS["default"])
    print_banner(slot, f"auto — scenario '{scenario_name}' {scenario}")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY in .env or environment")
        sys.exit(1)

    orch = Orchestrator(api_key)

    outcome_queue = list(scenario)
    pending_outcome = threading.Event()
    pending_patient = {"name": "", "channel": ""}

    def on_call(patient):
        pending_patient["name"] = patient["name"]
        pending_patient["channel"] = "call"
        pending_outcome.set()

    def on_sms(patient, slot_info):
        pending_patient["name"] = patient["name"]
        pending_patient["channel"] = "sms"
        pending_outcome.set()

    orch.on_voice_call = on_call
    orch.on_sms = on_sms

    print("Starting agent...\n")
    orch.start(slot)

    while True:
        if not pending_outcome.is_set():
            break

        pending_outcome.clear()
        name = pending_patient["name"]
        channel = pending_patient["channel"]

        # Pop next outcome from scenario
        if outcome_queue:
            outcome = outcome_queue.pop(0)
        else:
            outcome = "no_answer" if channel == "call" else "no_reply"

        # Adjust for SMS channel
        if channel == "sms" and outcome == "no_answer":
            outcome = "no_reply"

        print(f"  [{channel.upper()}] {name} → {outcome}")
        orch.handle_outcome(name, outcome)

        if orch.candidates:
            any_confirmed = any(c["status"] == "confirmed" for c in orch.candidates)
            all_terminal = all(
                c["status"] in ("declined", "no_answer", "no_reply", "confirmed")
                for c in orch.candidates
            )
            if any_confirmed or all_terminal:
                break

    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    if orch.candidates:
        confirmed = [c for c in orch.candidates if c["status"] == "confirmed"]
        if confirmed:
            print(f"  Slot filled by: {confirmed[0]['name']}")
            print(f"  Revenue recovered: ${slot['value']}")
        else:
            print("  Slot unfilled — all candidates exhausted")

        contacted = [c for c in orch.candidates if c["status"] != "waiting"]
        print(f"  Candidates contacted: {len(contacted)}")
        for c in contacted:
            print(f"    {c['rank']}. {c['name']} — {c['status']}")
    print()


if __name__ == "__main__":
    # Parse args
    auto_mode = "--auto" in sys.argv

    # Pick slot type
    slot_type = "cleaning"
    if "--slot" in sys.argv:
        idx = sys.argv.index("--slot")
        if idx + 1 < len(sys.argv):
            slot_type = sys.argv[idx + 1]

    slot = DEMO_SLOTS.get(slot_type, DEMO_SLOT)

    # Pick scenario (auto mode only)
    scenario_name = "default"
    if "--scenario" in sys.argv:
        idx = sys.argv.index("--scenario")
        if idx + 1 < len(sys.argv):
            scenario_name = sys.argv[idx + 1]

    if "--list-scenarios" in sys.argv:
        print("Available scenarios:")
        for name, outcomes in SCENARIOS.items():
            print(f"  {name}: {outcomes}")
        sys.exit(0)

    if auto_mode:
        run_auto(slot, scenario_name)
    else:
        run_interactive(slot)
