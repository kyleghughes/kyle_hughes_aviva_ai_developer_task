import json
import urllib.error

import pytest

from app.llm import EmailLLM, LLMUnavailable
from app.models import Priority


def test_classify_parses_valid_json(monkeypatch):
    llm = EmailLLM()
    payload = {"topic": "claim", "actions": ["Review"], "urgency_signals": [], "importance_signals": [], "priority": "high", "summary": "S", "confidence": .8, "rationale": "R"}
    monkeypatch.setattr(llm, "_chat", lambda *args, **kwargs: json.dumps(payload))
    decision = llm.classify("email")
    assert decision.topic == "claim"
    assert decision.priority is Priority.HIGH


def test_classify_rejects_non_json(monkeypatch):
    llm = EmailLLM()
    monkeypatch.setattr(llm, "_chat", lambda *args, **kwargs: "not json")
    with pytest.raises(LLMUnavailable, match="non-JSON"):
        llm.classify("email")


def test_chat_connection_error_is_actionable(monkeypatch):
    llm = EmailLLM()
    def fail(*args, **kwargs):
        raise urllib.error.URLError("connection refused")
    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(LLMUnavailable, match="Cannot connect to Ollama"):
        llm._chat("system", "user")


def test_chat_404_mentions_pull_command(monkeypatch):
    llm = EmailLLM()
    class ErrorResponse:
        def read(self): return b'{"error":"not found"}'
    def fail(*args, **kwargs):
        error = urllib.error.HTTPError("url", 404, "not found", {}, None)
        error.read = lambda: b'{"error":"model missing"}'
        raise error
    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(LLMUnavailable, match="ollama pull"):
        llm._chat("system", "user")


def test_status_reports_missing_model(monkeypatch):
    llm = EmailLLM()
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"models": [{"name": "other:latest"}]}'
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    status = llm.status()
    assert status["available"] is True
    assert status["model_installed"] is False


def test_status_reports_connection_failure(monkeypatch):
    llm = EmailLLM()
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")))
    status = llm.status()
    assert status["available"] is False
    assert "Start Ollama" in status["message"]


def test_answer_parses_json(monkeypatch):
    llm = EmailLLM()
    result = {"answer": "The claim is open.", "suggested_questions": ["Who owns it?"]}
    monkeypatch.setattr(llm, "_chat", lambda *args, **kwargs: json.dumps(result))
    # answer uses its own HTTP request, so patch urlopen.
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return json.dumps({"message": {"content": json.dumps(result)}}).encode()
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    output = llm.answer("What happened?", "THREAD t")
    assert output["answer"] == "The claim is open."


def test_answer_rejects_invalid_answer(monkeypatch):
    llm = EmailLLM()
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"message":{"content":"{}"}}'
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(LLMUnavailable, match="no answer"):
        llm.answer("What?", "THREAD t")


def test_chat_json_mode_adds_format(monkeypatch):
    llm = EmailLLM()
    captured = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"message":{"content":"ok"}}'
    def fake(request, **kwargs):
        captured["body"] = json.loads(request.data)
        return Response()
    monkeypatch.setattr("urllib.request.urlopen", fake)
    assert llm._chat("system", "user", json_mode=True) == "ok"
    assert captured["body"]["format"] == "json"


def test_chat_rejects_invalid_transport_json(monkeypatch):
    llm = EmailLLM()
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b"not-json"
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(LLMUnavailable, match="invalid response"):
        llm._chat("system", "user")


def test_chat_rejects_missing_message(monkeypatch):
    llm = EmailLLM()
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{}'
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(LLMUnavailable, match="no model response"):
        llm._chat("system", "user")


def test_status_handles_http_error(monkeypatch):
    llm = EmailLLM()
    def fail(*args, **kwargs):
        raise urllib.error.HTTPError("url", 500, "boom", {}, None)
    monkeypatch.setattr("urllib.request.urlopen", fail)
    assert "HTTP 500" in llm.status()["message"]


def test_status_handles_invalid_json(monkeypatch):
    llm = EmailLLM()
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b"bad"
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    assert "invalid /api/tags" in llm.status()["message"]


def test_is_available_requires_model(monkeypatch):
    llm = EmailLLM()
    monkeypatch.setattr(llm, "status", lambda: {"available": True, "model_installed": False})
    assert not llm.is_available()
    monkeypatch.setattr(llm, "status", lambda: {"available": True, "model_installed": True})
    assert llm.is_available()


def test_answer_supports_history_and_workload_mode(monkeypatch):
    llm = EmailLLM()
    captured = {}
    result = {"answer": "focus", "suggested_questions": []}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return json.dumps({"message": {"content": json.dumps(result)}}).encode()
    def fake(request, **kwargs):
        captured["body"] = json.loads(request.data)
        return Response()
    monkeypatch.setattr("urllib.request.urlopen", fake)
    output = llm.answer("What first?", "THREAD t", mode="workload", history=[{"role": "user", "content": "Earlier"}, {"role": "system", "content": "ignore"}])
    assert output["answer"] == "focus"
    messages = captured["body"]["messages"]
    assert any(message["content"] == "Earlier" for message in messages)
    assert not any(message["content"] == "ignore" for message in messages)


def test_answer_handles_transport_and_content_errors(monkeypatch):
    llm = EmailLLM()
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline")))
    with pytest.raises(LLMUnavailable, match="Cannot connect"):
        llm.answer("q", "e")

    class EmptyResponse:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{}'
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: EmptyResponse())
    with pytest.raises(LLMUnavailable, match="no model response"):
        llm.answer("q", "e")


def test_answer_rejects_non_json_model_content(monkeypatch):
    llm = EmailLLM()
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'{"message":{"content":"not json"}}'
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(LLMUnavailable, match="non-JSON Q&A"):
        llm.answer("q", "e")


def test_answer_non_list_suggestions_are_ignored(monkeypatch):
    llm = EmailLLM()
    payload = {"answer": "ok", "suggested_questions": "bad"}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return json.dumps({"message": {"content": json.dumps(payload)}}).encode()
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: Response())
    assert llm.answer("q", "e")["suggested_questions"] == []
