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
        """Treatment match should give +150 bonus."""
        patient = {
            "treatment_needed": "cleaning",
            "days_overdue": 10,
            "reliability_score": 0.5,
        }
        slot = {"treatment": "cleaning"}

        score = score_candidate(patient, slot)

        # min(10,60)*2 + 150 + int(0.5*30) = 20 + 150 + 15 = 185
        assert score == 185

    def test_score_candidate_treatment_mismatch_penalty(self):
        """Treatment mismatch should give -200 penalty."""
        patient = {
            "treatment_needed": "filling",
            "days_overdue": 10,
            "reliability_score": 0.5,
        }
        slot = {"treatment": "cleaning"}

        score = score_candidate(patient, slot)

        # min(10,60)*2 - 200 + int(0.5*30) = 20 - 200 + 15 = -165
        assert score == -165

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
        # She should be ranked lower despite high days_overdue
        maria = next(c for c in candidates if c["name"] == "Maria Garcia")
        sarah = next(c for c in candidates if c["name"] == "Sarah Kim")

        assert sarah["rank"] < maria["rank"]

    def test_score_candidates_all_start_waiting(self):
        """All candidates should start with status 'waiting'."""
        candidates = score_candidates(RECALL_LIST, DEMO_SLOT)

        for c in candidates:
            assert c["status"] == "waiting"


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
