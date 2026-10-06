from datetime import datetime, timezone

from .models import AuditEvent


class AuditLog:
    """In-memory store for recent application audit events.

    The log is intentionally bounded so that application activity can be
    inspected during runtime without allowing the in-memory collection to
    grow indefinitely.
    """

    def __init__(self, limit: int = 100) -> None:
        """Initialise the audit log with a maximum number of retained events."""
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
        """Create, store, and return an audit event.

        Events are timestamped in UTC and may optionally include the
        associated thread, LLM model, rule version, and additional details.

        Only the most recent ``limit`` events are retained.
        """
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            thread_id=thread_id,
            model=model,
            rule_version=rule_version,
            details=details or {},
        )

        self.events.append(event)

        # Keep the in-memory audit log bounded by discarding older events.
        del self.events[:-self.limit]

        return event

    def recent(self) -> list[AuditEvent]:
        """Return the currently retained audit events.

        A new list is returned so callers cannot directly modify the
        audit log's internal collection.
        """
        return list(self.events)