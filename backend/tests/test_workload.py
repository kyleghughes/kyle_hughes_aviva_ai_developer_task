from datetime import datetime, timedelta, timezone

import pytest

from app.models import EmailType, WorkItem
from app.workload import paginate_work_items


def item(
    thread_id: str,
    kind: EmailType,
    days: int = 0,
    done: bool = False,
    subject: str | None = None,
) -> WorkItem:
    return WorkItem(
        thread_id=thread_id,
        subject=subject or f"Subject {thread_id}",
        latest_date=(
            datetime(2026, 1, 1, tzinfo=timezone.utc)
            + timedelta(days=days)
        ),
        sender=f"{thread_id}@example.com",
        email_type=kind,
        message_count=1,
        done=done,
    )


def test_search_matches_subject_sender_topic_and_summary():
    values = [
        item("abc", EmailType.ACTION, subject="Glass repair"),
        item("xyz", EmailType.ACTION, subject="Other"),
    ]
    values[1] = values[1].model_copy(update={"topic": "motor claim"})

    assert paginate_work_items(values, query="glass").items[0].thread_id == "abc"
    assert paginate_work_items(values, query="motor").items[0].thread_id == "xyz"
    assert paginate_work_items(values, query="xyz@example").items[0].thread_id == "xyz"


def test_pagination_returns_metadata_and_safe_last_page():
    values = [item(str(i), EmailType.ACTION, i) for i in range(25)]

    result = paginate_work_items(values, page=3, page_size=10)

    assert result.total == 25
    assert result.total_pages == 3
    assert result.page == 3
    assert len(result.items) == 5

    safe = paginate_work_items(values, page=99, page_size=10)
    assert safe.page == 3


def test_filters_apply_before_pagination():
    values = [
        item("a", EmailType.ACTION),
        item("i", EmailType.INFORMATIONAL),
        item("d", EmailType.ACTION, done=True),
    ]

    assert [
        x.thread_id
        for x in paginate_work_items(values, filter_name="action").items
    ] == ["a"]
    assert [
        x.thread_id
        for x in paginate_work_items(values, filter_name="done").items
    ] == ["d"]
    assert [
        x.thread_id
        for x in paginate_work_items(values, filter_name="all").items
    ] == ["a", "i"]


def test_invalid_pagination_arguments_are_rejected():
    with pytest.raises(ValueError):
        paginate_work_items([], page=0)

    with pytest.raises(ValueError):
        paginate_work_items([], page_size=101)

    with pytest.raises(ValueError):
        paginate_work_items([], filter_name="bad")
