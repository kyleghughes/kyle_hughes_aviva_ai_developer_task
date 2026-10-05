from app.audit import AuditLog


def test_audit_log_records_and_limits_events():
    audit = AuditLog(limit=2)
    audit.record("one", details={})
    audit.record("two", details={})
    audit.record("three", details={})
    events = audit.recent()
    assert [event.event_type for event in events] == ["two", "three"]
