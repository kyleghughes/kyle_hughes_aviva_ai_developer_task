import pytest

from app.llm import LLMUnavailable
from app.models import AskRequest, LLMDecision


def test_service_mark_done_missing_raises(ingested_service):
    with pytest.raises(KeyError):
        ingested_service.mark_done("missing", True)


def test_service_analyze_missing_raises(ingested_service):
    with pytest.raises(KeyError):
        ingested_service.analyze("missing")


def test_service_analyze_records_audit(ingested_service, monkeypatch):
    thread_id = next(iter(ingested_service.repo.work_items))
    decision = LLMDecision(topic="claim", summary="S", rationale="R", confidence=.7)
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
    assert captured["mode"] == "thread_search"
    assert thread_id in captured["evidence"]


def test_service_ask_workload(ingested_service, monkeypatch):
    captured = {}
    monkeypatch.setattr(ingested_service.llm, "answer", lambda question, evidence, mode, history: captured.update(mode=mode) or {"answer": "focus", "suggested_questions": ["Why?"]})
    result = ingested_service.ask(AskRequest(question="What should I prioritise?"))
    assert captured["mode"] == "workload"
    assert result.suggested_questions == ["Why?"]


def test_service_ask_propagates_llm_failure(ingested_service, monkeypatch):
    monkeypatch.setattr(ingested_service.llm, "answer", lambda *args, **kwargs: (_ for _ in ()).throw(LLMUnavailable("offline")))
    with pytest.raises(LLMUnavailable):
        ingested_service.ask(AskRequest(question="Tell me about the claim"))
