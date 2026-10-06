import pytest
from datetime import datetime, timezone

from app.models import EmailType, LLMDecision, Priority, WorkItem
from app.repository import MailboxRepository


def make_item(done=False):
    return WorkItem(
        thread_id="t1", subject="Test", latest_date=datetime.now(timezone.utc), sender="a@b.com",
        email_type=EmailType.ACTION, message_count=1, done=done,
    )


def test_done_state_updates_set_and_item():
    repo = MailboxRepository()
    repo.work_items["t1"] = make_item()
    assert repo.set_in_progress("t1", True).in_progress
    assert repo.set_done("t1", True).done
    assert "t1" in repo.done_thread_ids
    assert not repo.set_done("t1", False).done
    assert "t1" not in repo.done_thread_ids


def test_save_decision_updates_work_item():
    repo = MailboxRepository()
    repo.work_items["t1"] = make_item()
    decision = LLMDecision(topic="claims", summary="Summary", rationale="Reason", confidence=.8, priority=Priority.HIGH)
    updated = repo.save_decision("t1", decision)
    assert updated.topic == "claims"
    assert updated.priority is Priority.HIGH
    assert updated.analysis_status == "analyzed"
    assert repo.decisions["t1"] == decision


def test_invalidate_analysis_removes_decision():
    repo = MailboxRepository()
    repo.decisions["t1"] = LLMDecision(topic="x", summary="s", rationale="r", confidence=.5, priority=Priority.LOW)
    repo.invalidate_analysis("t1")
    assert "t1" not in repo.decisions


def test_email_type_override_updates_category_and_clears_done_for_archive():
    repo = MailboxRepository()
    repo.work_items["t1"] = make_item(done=True)

    updated = repo.set_email_type("t1", EmailType.INFORMATIONAL)

    assert updated.email_type is EmailType.INFORMATIONAL
    assert updated.done is False
    assert repo.type_overrides["t1"] is EmailType.INFORMATIONAL
    assert "t1" not in repo.done_thread_ids


def test_in_progress_state_updates_and_rejects_done_item():
    repo = MailboxRepository()
    repo.work_items["t1"] = make_item()
    started = repo.set_in_progress("t1", True)
    assert started.in_progress
    actioned = repo.set_done("t1", True)
    assert actioned.done
    assert not actioned.in_progress
    with pytest.raises(ValueError):
        repo.set_in_progress("t1", True)


def test_pinned_state_updates_and_persists_in_item():
    repo = MailboxRepository()
    repo.work_items["t1"] = make_item()

    pinned = repo.set_pinned("t1", True)
    assert pinned.pinned is True
    assert "t1" in repo.pinned_thread_ids

    unpinned = repo.set_pinned("t1", False)
    assert unpinned.pinned is False
    assert "t1" not in repo.pinned_thread_ids


def test_priority_override_updates_work_item_and_survives_saved_decision():
    repo = MailboxRepository()
    repo.work_items["t1"] = make_item()
    decision = LLMDecision(topic="claims", summary="Summary", rationale="Reason", confidence=.8, priority=Priority.HIGH)
    repo.save_decision("t1", decision)
    updated = repo.set_priority("t1", Priority.LOW)
    assert updated.priority is Priority.LOW
    refreshed = repo.save_decision("t1", decision)
    assert refreshed.priority is Priority.LOW
    assert repo.priority_overrides["t1"] is Priority.LOW


def test_invalidate_analysis_clears_priority_override():
    repo = MailboxRepository()
    repo.work_items["t1"] = make_item()
    repo.priority_overrides["t1"] = Priority.LOW
    repo.decisions["t1"] = LLMDecision(topic="x", summary="s", rationale="r", confidence=.5, priority=Priority.HIGH)
    repo.invalidate_analysis("t1")
    assert "t1" not in repo.priority_overrides
