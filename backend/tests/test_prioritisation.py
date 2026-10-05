from datetime import datetime, timezone

from app.models import Email, EmailType, WorkItem
from app.prioritisation import count_work_items, classify_thread, sort_work_items


def email(body: str, subject: str = "Test", to=None) -> Email:
    return Email(
        body=body,
        subject=subject,
        sent_from="sender@example.com",
        sent_to=to or ["other@example.com"],
        date_sent=datetime(2026, 1, 1, tzinfo=timezone.utc),
        message_id="m1",
        thread_id="t1",
    )


def work_item(
    thread_id: str,
    kind: EmailType,
    days: int = 0,
    done: bool = False,
) -> WorkItem:
    return WorkItem(
        thread_id=thread_id,
        subject=f"Subject {thread_id}",
        latest_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        sender=f"{thread_id}@example.com",
        email_type=kind,
        message_count=1,
        done=done,
    )


def test_sort_is_deterministic_and_done_items_are_last():
    values = [
        work_item("i", EmailType.INFORMATIONAL),
        work_item("a", EmailType.ACTION),
        work_item("d", EmailType.ACTION, done=True),
        work_item("r", EmailType.IRRELEVANT),
    ]

    assert [x.thread_id for x in sort_work_items(values)] == ["a", "i", "r", "d"]


def test_counts_cover_open_and_done_states():
    values = [
        work_item("a", EmailType.ACTION),
        work_item("i", EmailType.INFORMATIONAL),
        work_item("r", EmailType.IRRELEVANT),
        work_item("d", EmailType.ACTION, done=True),
    ]

    assert count_work_items(values) == {
        "action": 1,
        "informational": 1,
        "irrelevant": 1,
        "done": 1,
        "pending": 3,
    }


def test_explicit_action_wins_over_marketing_language():
    result, reasons = classify_thread([email("Special offer — please review the attached claim")])
    assert result is EmailType.ACTION
    assert "please review" in reasons[0]


def test_no_action_required_is_informational():
    result, reasons = classify_thread([email("For your information: no action required.")])
    assert result is EmailType.INFORMATIONAL
    assert reasons == ["Explicitly states that no action is required"]


def test_fyi_without_action_is_informational():
    result, _ = classify_thread([email("FYI, the repair is complete.")])
    assert result is EmailType.INFORMATIONAL


def test_marketing_without_action_is_irrelevant():
    result, _ = classify_thread([email("Newsletter: special offer this week")])
    assert result is EmailType.IRRELEVANT


def test_direct_handler_mailbox_is_actionable(monkeypatch):
    monkeypatch.setenv("HANDLER_MAILBOX", "handler@example.com")
    result, reasons = classify_thread([email("Here is the claim update.", to=["handler@example.com"])])
    assert result is EmailType.ACTION
    assert "handler mailbox" in reasons[0]


def test_non_action_relevant_mail_is_informational():
    result, reasons = classify_thread([email("The claimant has supplied additional context.")])
    assert result is EmailType.INFORMATIONAL
    assert "Relevant mailbox" in reasons[0]
