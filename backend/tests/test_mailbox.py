import json
from datetime import datetime, timezone

from app.mailbox import JsonMailboxSource, format_email, format_thread
from app.models import Email, Thread


def make_thread():
    messages = [
        Email(body="Later", subject="S", sent_from="a", sent_to=["b"], date_sent=datetime(2026, 1, 2, tzinfo=timezone.utc), message_id="2", thread_id="t"),
        Email(body="Earlier", subject="S", sent_from="a", sent_to=["b"], date_sent=datetime(2026, 1, 1, tzinfo=timezone.utc), message_id="1", thread_id="t"),
    ]
    return Thread(messages=messages)


def test_format_email_contains_headers_and_body():
    text = format_email(make_thread().messages[0])
    assert "MESSAGE 2" in text
    assert "From: a" in text
    assert "Body:\nLater" in text


def test_format_thread_orders_by_date():
    text = format_thread(make_thread())
    assert text.index("MESSAGE 1") < text.index("MESSAGE 2")


def test_json_source_reads_threads(tmp_path):
    path = tmp_path / "mail.json"
    path.write_text(json.dumps({"emails": [make_thread().model_dump(mode="json")]}))
    result = JsonMailboxSource(path).read()
    assert len(result) == 1
    assert result[0].messages[0].thread_id == "t"
