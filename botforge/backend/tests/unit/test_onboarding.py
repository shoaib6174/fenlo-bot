"""Unit tests for onboarding API helpers and model."""

from app.api.onboarding import _compute_completion_pct, _next_incomplete_step
from app.models.onboarding import ONBOARDING_STEPS, OnboardingProgress


class TestCompletionPct:
    """Test completion percentage calculation."""

    def test_all_false_returns_zero(self):
        steps = dict.fromkeys(ONBOARDING_STEPS, False)
        assert _compute_completion_pct(steps) == 0

    def test_all_true_returns_100(self):
        steps = dict.fromkeys(ONBOARDING_STEPS, True)
        assert _compute_completion_pct(steps) == 100

    def test_partial_completion(self):
        steps = dict.fromkeys(ONBOARDING_STEPS, False)
        steps["personality"] = True
        steps["first_document"] = True
        # 2/5 = 40%
        assert _compute_completion_pct(steps) == 40

    def test_empty_dict_returns_zero(self):
        assert _compute_completion_pct({}) == 0

    def test_none_returns_zero(self):
        assert _compute_completion_pct(None) == 0


class TestNextIncompleteStep:
    """Test next incomplete step finder."""

    def test_all_incomplete_returns_first(self):
        steps = dict.fromkeys(ONBOARDING_STEPS, False)
        assert _next_incomplete_step(steps) == "personality"

    def test_first_done_returns_second(self):
        steps = dict.fromkeys(ONBOARDING_STEPS, False)
        steps["personality"] = True
        assert _next_incomplete_step(steps) == "first_document"

    def test_all_done_returns_none(self):
        steps = dict.fromkeys(ONBOARDING_STEPS, True)
        assert _next_incomplete_step(steps) is None

    def test_skipped_middle_returns_first_gap(self):
        """If user completes steps out of order, returns first incomplete."""
        steps = dict.fromkeys(ONBOARDING_STEPS, False)
        steps["personality"] = True
        steps["test_chat"] = True  # skipped first_document
        assert _next_incomplete_step(steps) == "first_document"


class TestOnboardingSteps:
    """Test onboarding step definitions."""

    def test_steps_count(self):
        assert len(ONBOARDING_STEPS) == 5

    def test_steps_order(self):
        assert ONBOARDING_STEPS[0] == "personality"
        assert ONBOARDING_STEPS[-1] == "complete"

    def test_model_default_step_completed(self):
        """Model server_default should include all 5 steps as false."""
        col = OnboardingProgress.__table__.columns["step_completed"]
        default_text = col.server_default.arg
        for step in ONBOARDING_STEPS:
            assert f'"{step}": false' in default_text
