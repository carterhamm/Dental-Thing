"""
Tests for brain.py — Eddy, run these to validate your implementation.

Usage:
    cd backend/
    python -m pytest test_brain.py -v

All tests should pass before handing off to Spencer.
"""

import pytest
from brain import (
    score_candidates,
    get_next_action,
    update_candidate_status,
    calculate_recovered_revenue,
    RECALL_LIST,
)

SLOT = {
    "treatment": "cleaning",
    "time": "2:00 PM",
    "date": "Today",
    "value": 200,
}


class TestScoreCandidates:
    def test_returns_ranked_list(self):
        result = score_candidates(RECALL_LIST, SLOT)
        assert isinstance(result, list)
        assert len(result) == len(RECALL_LIST)

    def test_has_required_fields(self):
        result = score_candidates(RECALL_LIST, SLOT)
        for candidate in result:
            assert "rank" in candidate
            assert "name" in candidate
            assert "phone" in candidate
            assert "score" in candidate
            assert "status" in candidate
            assert "treatment_needed" in candidate
            assert "days_overdue" in candidate

    def test_all_statuses_are_waiting(self):
        result = score_candidates(RECALL_LIST, SLOT)
        for candidate in result:
            assert candidate["status"] == "waiting"

    def test_ranked_by_score_descending(self):
        result = score_candidates(RECALL_LIST, SLOT)
        scores = [c["score"] for c in result]
        assert scores == sorted(scores, reverse=True)

    def test_ranks_are_sequential(self):
        result = score_candidates(RECALL_LIST, SLOT)
        ranks = [c["rank"] for c in result]
        assert ranks == list(range(1, len(result) + 1))

    def test_treatment_match_boosts_score(self):
        """Candidates needing 'cleaning' should score higher than 'filling' for a cleaning slot."""
        result = score_candidates(RECALL_LIST, SLOT)
        cleaning_scores = [c["score"] for c in result if c["treatment_needed"] == "cleaning"]
        filling_scores = [c["score"] for c in result if c["treatment_needed"] == "filling"]
        if cleaning_scores and filling_scores:
            # At least the best cleaning candidate should beat the best filling candidate
            assert max(cleaning_scores) > max(filling_scores)

    def test_scores_are_0_to_100(self):
        result = score_candidates(RECALL_LIST, SLOT)
        for candidate in result:
            assert 0 <= candidate["score"] <= 100


class TestGetNextAction:
    def _make_candidates(self, statuses):
        return [
            {"rank": i + 1, "name": f"Patient {i}", "phone": f"+1-555-000{i}",
             "score": 90 - i * 10, "status": s, "treatment_needed": "cleaning",
             "days_overdue": 10}
            for i, s in enumerate(statuses)
        ]

    def test_first_call_starts_with_index_0(self):
        candidates = self._make_candidates(["waiting", "waiting"])
        action, idx = get_next_action(candidates, -1)
        assert action == "call"
        assert idx == 0

    def test_waiting_candidate_gets_called(self):
        candidates = self._make_candidates(["waiting", "waiting"])
        action, idx = get_next_action(candidates, 0)
        assert action == "call"
        assert idx == 0

    def test_no_answer_falls_back_to_sms(self):
        candidates = self._make_candidates(["no_answer", "waiting"])
        action, idx = get_next_action(candidates, 0)
        assert action == "sms"
        assert idx == 0

    def test_declined_moves_to_next(self):
        candidates = self._make_candidates(["declined", "waiting"])
        action, idx = get_next_action(candidates, 0)
        assert action == "next_candidate"
        assert idx == 1

    def test_confirmed_returns_done(self):
        candidates = self._make_candidates(["confirmed", "waiting"])
        action, idx = get_next_action(candidates, 0)
        assert action == "done"
        assert idx == 0

    def test_all_exhausted_gives_up(self):
        candidates = self._make_candidates(["declined", "declined"])
        action, idx = get_next_action(candidates, 1)
        assert action == "give_up"
        assert idx == -1

    def test_empty_candidates_gives_up(self):
        action, idx = get_next_action([], -1)
        assert action == "give_up"
        assert idx == -1


class TestUpdateCandidateStatus:
    def test_updates_correct_candidate(self):
        candidates = [
            {"name": "A", "status": "waiting"},
            {"name": "B", "status": "waiting"},
        ]
        result = update_candidate_status(candidates, 0, "calling")
        assert result[0]["status"] == "calling"
        assert result[1]["status"] == "waiting"

    def test_does_not_mutate_input(self):
        candidates = [{"name": "A", "status": "waiting"}]
        result = update_candidate_status(candidates, 0, "calling")
        assert candidates[0]["status"] == "waiting"  # original unchanged
        assert result[0]["status"] == "calling"


class TestCalculateRecoveredRevenue:
    def test_returns_slot_value(self):
        assert calculate_recovered_revenue({"value": 200}) == 200

    def test_returns_zero_for_missing_value(self):
        assert calculate_recovered_revenue({}) == 0
