"""The worker re-scores a changed card at once, unless it was scored within the cooldown."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.card_classifier import CardVerdict, assess
from app.rate_limits import NOT_SENT, RescoreCooldownError

from .conftest import MOCK_AGENT_CARD
from .test_card_classifier import UNMETERED
from .test_endpoints import _make_agent_public

COOLDOWN = timedelta(hours=6)
CLEAN = CardVerdict(score=0.1, signals={}, model="jev-test")
CHANGED = {"record": {"name": "changed"}}


def _ago(hours):
    return datetime.now(timezone.utc) - timedelta(hours=hours)


async def _assess(state, cooldown=COOLDOWN, document=CHANGED):
    with patch("app.card_classifier.classify_card", new=AsyncMock(return_value=CLEAN)) as classify:
        review = await assess(state, document, budget=UNMETERED, may_grandfather=False, cooldown=cooldown)
    return review, classify


async def test_a_repeat_change_inside_the_window_waits_without_sending():
    with pytest.raises(RescoreCooldownError):
        await _assess({"jev_card_sha256": "old", "jev_checked_at": _ago(1)})


@pytest.mark.parametrize("checked_at", [None, _ago(6.01), _ago(48)], ids=["never-scored", "just-outside", "long-ago"])
async def test_a_change_after_a_quiet_window_is_rescored_at_once(checked_at):
    review, classify = await _assess({"jev_card_sha256": "old", "jev_checked_at": checked_at})
    classify.assert_awaited_once()
    assert review is not None and review.verdict is CLEAN


async def test_an_unscored_agent_is_retried_inside_the_window():
    review, classify = await _assess({"review_status": "unscored", "jev_card_sha256": "old", "jev_checked_at": _ago(1)})
    classify.assert_awaited_once()


async def test_unchanged_content_inside_the_window_is_simply_skipped():
    from app.card_classifier import card_sha256

    review, classify = await _assess({"jev_card_sha256": card_sha256(CHANGED), "jev_checked_at": _ago(1)})
    assert review is None
    classify.assert_not_awaited()


async def test_callers_without_a_cooldown_never_wait():
    """Registrations and admin updates pass no cooldown."""
    review, classify = await _assess({"jev_card_sha256": "old", "jev_checked_at": _ago(0.01)}, cooldown=None)
    classify.assert_awaited_once()


async def test_the_worker_writes_nothing_while_a_change_waits():
    import worker

    stored = _make_agent_public()
    repo = SimpleNamespace(
        get_review_snapshot=AsyncMock(return_value=(
            stored, {"jev_card_sha256": "old", "review_revision": 2, "jev_checked_at": _ago(1)},
        )),
        update_card_metadata=AsyncMock(),
    )
    jev = AsyncMock()
    with patch("app.card_classifier.classify_card", new=jev), \
         patch.object(worker, "_material_changes", return_value=({"name": "changed"}, {"name": "changed"})), \
         pytest.raises(NOT_SENT):
        await worker.refresh_agent_metadata(stored, dict(MOCK_AGENT_CARD), repo, conformance_errors=[], classify=True)
    jev.assert_not_awaited()
    repo.update_card_metadata.assert_not_awaited()


def test_the_cooldown_is_a_setting_defaulting_to_six_hours():
    from app.config import settings

    assert settings.rescore_cooldown_hours == 6.0
