import pytest

from app.llm import LLMUnavailable
from app.models import AskRequest, EmailType, LLMDecision, Priority


def test_service_mark_done_missing_raises(ingested_service):
    with pytest.raises(KeyError):
        ingested_service.mark_done("missing", True)


def test_service_analyze_missing_raises(ingested_service):
    with pytest.raises(KeyError):
        ingested_service.analyze("missing")


def test_service_analyze_records_audit(ingested_service, monkeypatch):
    thread_id = next(item.thread_id for item in ingested_service.repo.work_items.values() if item.email_type is EmailType.ACTION)
    decision = LLMDecision(topic="claim", summary="S", rationale="R", confidence=.7, priority=Priority.HIGH)
    monkeypatch.setattr(ingested_service.ingestion, "analyze_thread", lambda _: decision)
    result, item = ingested_service.analyze(thread_id)
    assert result == decision
    assert item.thread_id == thread_id
    assert ingested_service.audit.recent()[-1].event_type == "llm_analysis"


def test_service_ask_unrelated_question(ingested_service, monkeypatch):
    monkeypatch.setattr("app.services.retrieve", lambda repo, question: [])
    result = ingested_service.ask(AskRequest(question="What colour is the sky?"))
    assert result.thread_ids == []


def test_service_ask_thread_context(ingested_service, monkeypatch):
    thread_id = next(iter(ingested_service.repo.work_items))
    captured = {}
    monkeypatch.setattr(ingested_service.llm, "answer", lambda question, evidence, mode, history: captured.update(mode=mode, evidence=evidence) or {"answer": "ok", "suggested_questions": []})
    result = ingested_service.ask(AskRequest(question="What happened?", thread_id=thread_id))
    assert result.thread_ids == [thread_id]
    assert result.thread_titles[thread_id] == ingested_service.repo.work_items[thread_id].subject
    assert captured["mode"] == "thread_search"
    assert ingested_service.repo.work_items[thread_id].subject in captured["evidence"]
    assert thread_id not in captured["evidence"]


def test_service_ask_workload(ingested_service, monkeypatch):
    captured = {}
    monkeypatch.setattr(ingested_service.llm, "answer", lambda question, evidence, mode, history: captured.update(mode=mode, evidence=evidence) or {"answer": "focus", "suggested_questions": ["Why?"]})
    result = ingested_service.ask(AskRequest(question="What should I prioritise?"))
    assert captured["mode"] == "workload"
    assert result.suggested_questions == ["Why?"]
    assert result.thread_titles
    for thread_id, title in result.thread_titles.items():
        assert thread_id in result.thread_ids
        assert title == ingested_service.repo.work_items[thread_id].subject


def test_service_ask_propagates_llm_failure(ingested_service, monkeypatch):
    monkeypatch.setattr(ingested_service.llm, "answer", lambda *args, **kwargs: (_ for _ in ()).throw(LLMUnavailable("offline")))
    with pytest.raises(LLMUnavailable):
        ingested_service.ask(AskRequest(question="Tell me about the claim"))


def test_service_type_change_clears_analysis(ingested_service, monkeypatch):
    thread_id = next(item.thread_id for item in ingested_service.repo.work_items.values() if item.email_type is EmailType.ACTION)
    decision = LLMDecision(topic="claim", summary="S", rationale="R", confidence=.7, priority=Priority.HIGH)
    monkeypatch.setattr(ingested_service.ingestion, "analyze_thread", lambda _: decision)
    ingested_service.analyze(thread_id)

    updated = ingested_service.set_email_type(thread_id, EmailType.INFORMATIONAL)
    assert updated.analysis_status == "not_analyzed"
    assert updated.priority is None
    assert thread_id not in ingested_service.repo.decisions


def test_service_type_change_back_to_actionable_resets_analysis(ingested_service, monkeypatch):
    thread_id = next(item.thread_id for item in ingested_service.repo.work_items.values() if item.email_type is EmailType.ACTION)
    decision = LLMDecision(topic="claim", summary="S", rationale="R", confidence=.7, priority=Priority.HIGH)
    monkeypatch.setattr(ingested_service.ingestion, "analyze_thread", lambda _: decision)

    ingested_service.analyze(thread_id)
    ingested_service.set_email_type(thread_id, EmailType.INFORMATIONAL)
    updated = ingested_service.set_email_type(thread_id, EmailType.ACTION)

    assert updated.email_type is EmailType.ACTION
    assert updated.analysis_status == "not_analyzed"
    assert updated.priority is None
    assert updated.summary == "Awaiting AI analysis when opened."
    assert thread_id not in ingested_service.repo.decisions


def test_service_set_pinned_records_audit(ingested_service):
    thread_id = next(iter(ingested_service.repo.work_items))
    updated = ingested_service.set_pinned(thread_id, True)
    assert updated.pinned is True
    assert ingested_service.audit.recent()[-1].event_type == "work_item_pinned"

    updated = ingested_service.set_pinned(thread_id, False)
    assert updated.pinned is False
    assert ingested_service.audit.recent()[-1].event_type == "work_item_unpinned"


def test_service_priority_override_requires_analysis(ingested_service):
    thread_id = next(iter(ingested_service.repo.work_items))
    with pytest.raises(ValueError):
        ingested_service.set_priority(thread_id, Priority.LOW)


def test_service_priority_override_records_audit(ingested_service, monkeypatch):
    thread_id = next(item.thread_id for item in ingested_service.repo.work_items.values() if item.email_type is EmailType.ACTION)
    decision = LLMDecision(topic="claim", summary="S", rationale="R", confidence=.7, priority=Priority.HIGH)
    monkeypatch.setattr(ingested_service.ingestion, "analyze_thread", lambda _: decision)
    ingested_service.analyze(thread_id)
    ingested_service.repo.save_decision(thread_id, decision)
    updated = ingested_service.set_priority(thread_id, Priority.LOW)
    assert updated.priority is Priority.LOW
    assert ingested_service.audit.recent()[-1].event_type == "work_item_priority_changed"
