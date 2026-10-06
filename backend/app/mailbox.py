import json
from pathlib import Path

from .models import Email, Thread


def format_email(email: Email) -> str:
    """Format a single email as readable text.

    The resulting representation is used both for display and as the
    structured text supplied to the LLM during thread analysis.
    """
    return (
        f"MESSAGE {email.message_id}\n"
        f"From: {email.sent_from}\n"
        f"To: {', '.join(email.sent_to)}\n"
        f"Date: {email.date_sent.isoformat()}\n"
        f"Subject: {email.subject}\n"
        f"Body:\n{email.body}\n"
    )


def format_thread(thread: Thread) -> str:
    """Format all messages in a thread in chronological order.

    Messages are explicitly sorted by sent date so the resulting text
    reflects the progression of the conversation regardless of the order
    in which messages appear in the source JSON.
    """
    messages = sorted(
        thread.messages,
        key=lambda item: item.date_sent,
    )

    return "\n---\n".join(
        format_email(message)
        for message in messages
    )


class JsonMailboxSource:
    """Read and validate mailbox threads from a JSON file."""

    def __init__(self, path: str | Path) -> None:
        """Set the path to the mailbox JSON file."""
        self.path = Path(path)

    def read(self) -> list[Thread]:
        """Read the mailbox file and validate its threads.

        The source file is expected to contain an ``emails`` collection.
        Each entry is validated against the ``Thread`` model before being
        returned to the rest of the application.
        """
        raw = json.loads(
            self.path.read_text(),
        )

        return [
            Thread.model_validate(thread)
            for thread in raw["emails"]
        ]