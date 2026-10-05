from datetime import datetime, timezone

from app.models import EmailType, LLMDecision, WorkItem
from app.repository import MailboxRepository


def make_item(done=False):
    return WorkItem(
        thread_id="t1", subject="Test", latest_date=datetime.now(timezone.utc), sender="a@b.com",
        email_type=EmailType.ACTION, message_count=1, done=done,
    )


def test_done_state_updates_set_and_item():
    repo = MailboxRepository()
    repo.work_items["t1"] = make_item()
    assert repo.set_done("t1", True).done
    assert "t1" in repo.done_thread_ids
    assert not repo.set_done("t1", False).done
    assert "t1" not in repo.done_thread_ids


def test_save_decision_updates_work_item():
    repo = MailboxRepository()
    repo.work_items["t1"] = make_item()
    decision = LLMDecision(topic="claims", summary="Summary", rationale="Reason", confidence=.8)
    updated = repo.save_decision("t1", decision)
    assert updated.topic == "claims"
    assert updated.analysis_status == "analyzed"
    assert repo.decisions["t1"] == decision


def test_invalidate_analysis_removes_decision():
    repo = MailboxRepository()
    repo.decisions["t1"] = LLMDecision(topic="x", summary="s", rationale="r", confidence=.5)
    repo.invalidate_analysis("t1")
    assert "t1" not in repo.decisions
