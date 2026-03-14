"""
Key tests for the dental rescheduling agent brain module.

Tests cover:
1. Scoring ranks candidates correctly
2. get_next_action happy path
3. get_next_action fallback to SMS
4. get_next_action exhausted candidates
"""

import pytest

from agent.brain import (
    score_candidate,
    score_candidates,
    get_next_action,
    update_candidate_status,
    calculate_recovered_revenue,
    RECALL_LIST,
    DEMO_SLOT,
)


class TestScoring:
    """Tests for candidate scoring logic."""

    def test_score_candidate_treatment_match_bonus(self):
        """Treatment match should give +100 bonus."""
        patient = {
            "treatment_needed": "cleaning",
            "cycles_overdue": 1,
            "reliability_score": 0.5,
            "preferred_time_of_day": "afternoon",
            "pending_treatment": False,
        }
        slot = {"treatment": "cleaning", "time": "2:00 PM"}

        score = score_candidate(patient, slot)

        # cycles: 1*25=25, treatment: +100, reliability: 0.5*20=10, time match: +10, pending: 0
        # Total: 25 + 100 + 10 + 10 = 145
        assert score == 145

    def test_score_candidate_treatment_mismatch_penalty(self):
        """Treatment mismatch should give -50 penalty."""
        patient = {
            "treatment_needed": "filling",
            "cycles_overdue": 1,
            "reliability_score": 0.5,
            "preferred_time_of_day": "morning",
            "pending_treatment": False,
        }
        slot = {"treatment": "cleaning", "time": "2:00 PM"}

        score = score_candidate(patient, slot)

        # cycles: 1*25=25, treatment: -50, reliability: 0.5*20=10, time match: 0, pending: 0
        # Total: 25 - 50 + 10 = -15
        assert score == -15

    def test_score_candidate_pending_treatment_bonus(self):
        """Pending treatment should give +25 bonus."""
        patient = {
            "treatment_needed": "cleaning",
            "cycles_overdue": 1,
            "reliability_score": 0.5,
            "preferred_time_of_day": "afternoon",
            "pending_treatment": True,
        }
        slot = {"treatment": "cleaning", "time": "2:00 PM"}

        score = score_candidate(patient, slot)

        # cycles: 25, treatment: +100, reliability: 10, time match: +10, pending: +25
        # Total: 25 + 100 + 10 + 10 + 25 = 170
        assert score == 170

    def test_score_candidate_multiple_cycles_overdue(self):
        """Multiple cycles overdue should increase urgency."""
        patient_1_cycle = {
            "treatment_needed": "cleaning",
            "cycles_overdue": 1,
            "reliability_score": 0.5,
            "preferred_time_of_day": "afternoon",
            "pending_treatment": False,
        }
        patient_2_cycles = {
            "treatment_needed": "cleaning",
            "cycles_overdue": 2,
            "reliability_score": 0.5,
            "preferred_time_of_day": "afternoon",
            "pending_treatment": False,
        }
        slot = {"treatment": "cleaning", "time": "2:00 PM"}

        score_1 = score_candidate(patient_1_cycle, slot)
        score_2 = score_candidate(patient_2_cycles, slot)

        # 2 cycles should be 25 points higher than 1 cycle
        assert score_2 == score_1 + 25

    def test_score_candidates_ranks_correctly(self):
        """Candidates should be ranked by score descending."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)

        # Top candidate should be a cleaning patient (treatment match)
        assert candidates[0]["treatment_needed"] == "cleaning"
        assert candidates[0]["rank"] == 1

        # Verify scores are descending
        for i in range(len(candidates) - 1):
            assert candidates[i]["score"] >= candidates[i + 1]["score"]

    def test_score_candidates_treatment_match_ranks_higher(self):
        """Treatment-matched patients should rank higher than non-matched."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)

        # Maria Garcia needs "filling", not "cleaning"
        # Even with pending_treatment, she should rank lower than cleaning patients
        maria = next(c for c in candidates if c["name"] == "Maria Garcia")
        sarah = next(c for c in candidates if c["name"] == "Sarah Kim")

        assert sarah["rank"] < maria["rank"]

    def test_score_candidates_all_start_waiting(self):
        """All candidates should start with status 'waiting'."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)

        for c in candidates:
            assert c["status"] == "waiting"

    def test_score_candidates_includes_new_fields(self):
        """Candidates should include all the new fields."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)

        for c in candidates:
            assert "cycles_overdue" in c
            assert "preferred_time_of_day" in c
            assert "pending_treatment" in c


class TestGetNextAction:
    """Tests for the decision logic."""

    def test_happy_path_starts_with_call(self):
        """First action should be to call the first candidate."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)

        action, idx = get_next_action(candidates, current_index=-1)

        assert action == "call"
        assert idx == 0

    def test_happy_path_done_when_confirmed(self):
        """Should return 'done' when a candidate is confirmed."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)
        candidates = update_candidate_status(candidates, 0, "confirmed")

        action, idx = get_next_action(candidates, current_index=0)

        assert action == "done"
        assert idx == 0

    def test_fallback_to_sms_on_no_answer(self):
        """Should try SMS when call results in no_answer."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)
        candidates = update_candidate_status(candidates, 0, "no_answer")

        action, idx = get_next_action(candidates, current_index=0)

        assert action == "sms"
        assert idx == 0

    def test_wait_while_calling(self):
        """Should wait while call is in progress (before timeout)."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)
        candidates = update_candidate_status(candidates, 0, "calling")

        action, idx = get_next_action(candidates, current_index=0, elapsed_time=5.0)

        assert action == "wait"
        assert idx == 0

    def test_sms_fallback_on_call_timeout(self):
        """Should fall back to SMS when call times out."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)
        candidates = update_candidate_status(candidates, 0, "calling")

        action, idx = get_next_action(candidates, current_index=0, elapsed_time=35.0)

        assert action == "sms"
        assert idx == 0

    def test_next_candidate_on_decline(self):
        """Should move to next candidate when declined."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)
        candidates = update_candidate_status(candidates, 0, "declined")

        action, idx = get_next_action(candidates, current_index=0)

        assert action == "next_candidate"
        assert idx == 1

    def test_give_up_when_all_exhausted(self):
        """Should give up when all candidates are terminal."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)

        # Mark all candidates as declined
        for i in range(len(candidates)):
            candidates = update_candidate_status(candidates, i, "declined")

        action, idx = get_next_action(candidates, current_index=len(candidates) - 1)

        assert action == "give_up"
        assert idx == -1

    def test_give_up_on_empty_list(self):
        """Should give up immediately if no candidates."""
        action, idx = get_next_action([], current_index=-1)

        assert action == "give_up"
        assert idx == -1


class TestUpdateCandidateStatus:
    """Tests for status update function."""

    def test_updates_correct_candidate(self):
        """Should update only the specified candidate."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)
        original_statuses = [c["status"] for c in candidates]

        updated = update_candidate_status(candidates, 1, "calling")

        # Only index 1 should change
        assert updated[1]["status"] == "calling"
        assert updated[0]["status"] == original_statuses[0]
        assert updated[2]["status"] == original_statuses[2]

    def test_does_not_mutate_original(self):
        """Should return a new list, not mutate the original."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)
        original_status = candidates[0]["status"]

        updated = update_candidate_status(candidates, 0, "calling")

        # Original should be unchanged
        assert candidates[0]["status"] == original_status
        # Updated should be different
        assert updated[0]["status"] == "calling"


class TestCalculateRecoveredRevenue:
    """Tests for revenue calculation."""

    def test_returns_slot_value(self):
        """Should return the slot's value."""
        slot = {"value": 200}

        revenue = calculate_recovered_revenue(slot)

        assert revenue == 200

    def test_handles_missing_value(self):
        """Should return 0 if value is missing."""
        slot = {}

        revenue = calculate_recovered_revenue(slot)

        assert revenue == 0
