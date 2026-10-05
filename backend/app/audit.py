from datetime import datetime, timezone
from .models import AuditEvent


class AuditLog:
    """Small in-memory audit store for application events."""

    def __init__(self, limit: int = 100) -> None:
        """Initialise the audit store with a maximum event count."""
        self.limit = limit
        self.events: list[AuditEvent] = []

    def record(
        self,
        event_type: str,
        *,
        thread_id: str | None = None,
        model: str | None = None,
        rule_version: str | None = None,
        details: dict | None = None,
    ) -> AuditEvent:
        """Record an event and retain only the most recent entries."""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            thread_id=thread_id,
            model=model,
            rule_version=rule_version,
            details=details or {},
        )

        self.events.append(event)

        # Keep the in-memory audit log bounded.
        del self.events[:-self.limit]

        return event

    def recent(self) -> list[AuditEvent]:
        """Return a copy of the retained audit events."""
        return list(self.events)