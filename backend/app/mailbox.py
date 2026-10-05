import json
from pathlib import Path

from .models import Email, Thread


def format_email(email: Email) -> str:
    """Format an email as text for display or LLM input."""
    return (
        f"MESSAGE {email.message_id}\n"
        f"From: {email.sent_from}\n"
        f"To: {', '.join(email.sent_to)}\n"
        f"Date: {email.date_sent.isoformat()}\n"
        f"Subject: {email.subject}\n"
        f"Body:\n{email.body}\n"
    )


def format_thread(thread: Thread) -> str:
    """Format a thread chronologically as text."""
    return "\n---\n".join(
        format_email(message)
        for message in sorted(
            thread.messages,
            key=lambda item: item.date_sent,
        )
    )


class JsonMailboxSource:
    """Reads mailbox threads from a JSON file."""

    def __init__(self, path: str | Path) -> None:
        """Set the mailbox file path."""
        self.path = Path(path)

    def read(self) -> list[Thread]:
        """Read and validate all mailbox threads."""
        raw = json.loads(self.path.read_text())

        return [
            Thread.model_validate(thread)
            for thread in raw["emails"]
        ]