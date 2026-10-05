from fastapi.testclient import TestClient

from app.api import create_app


def test_work_items_endpoint_supports_search_and_pagination(service):
    app = create_app(service)
    with TestClient(app) as client:
        response = client.get("/api/work-items?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 50
        assert data["total_pages"] == 10

        search = client.get("/api/work-items?q=PIN-HOM-501772&page_size=10")
        assert search.status_code == 200
        assert search.json()["total"] == 1


def test_work_items_endpoint_filter_and_page_clamping(service):
    app = create_app(service)
    with TestClient(app) as client:
        response = client.get("/api/work-items?filter=done&page=99")
        assert response.status_code == 200
        assert response.json()["page"] == 1
        assert response.json()["total"] == 0


def test_done_and_incomplete_endpoints(service):
    service.ingest()
    thread_id = next(iter(service.repo.work_items))
    app = create_app(service)
    with TestClient(app) as client:
        done = client.post(f"/api/work-items/{thread_id}/done")
        assert done.status_code == 200
        assert done.json()["done"] is True
        reopened = client.post(f"/api/work-items/{thread_id}/incomplete")
        assert reopened.status_code == 200
        assert reopened.json()["done"] is False


def test_missing_work_item_is_404(service):
    app = create_app(service)
    with TestClient(app) as client:
        assert client.post("/api/work-items/missing/done").status_code == 404
        assert client.get("/api/threads/missing").status_code == 404


def test_ingest_endpoint_and_audit(service):
    app = create_app(service)
    with TestClient(app) as client:
        response = client.post("/api/ingest")
        assert response.status_code == 200
        audit = client.get("/api/audit")
        assert audit.status_code == 200
        assert any(event["event_type"] == "mailbox_ingest" for event in audit.json())


def test_health_uses_llm_status(service, monkeypatch):
    monkeypatch.setattr(service.llm, "status", lambda: {"available": True, "model_installed": True, "url": "x", "model": "m", "models": ["m"], "message": "ready"})
    app = create_app(service)
    with TestClient(app) as client:
        data = client.get("/api/health").json()
        assert data["llm_configured"] is True


def test_analyze_endpoint_maps_llm_failure_to_503(service, monkeypatch):
    service.ingest()
    thread_id = next(iter(service.repo.work_items))
    from app.llm import LLMUnavailable
    monkeypatch.setattr(service.ingestion.llm, "classify", lambda _: (_ for _ in ()).throw(LLMUnavailable("Ollama unavailable")))
    app = create_app(service)
    with TestClient(app) as client:
        response = client.post(f"/api/work-items/{thread_id}/analyze")
        assert response.status_code == 503
        assert "Ollama unavailable" in response.json()["detail"]


def test_ask_endpoint_handles_empty_mailbox(service):
    app = create_app(service)
    # Lifespan normally ingests the source, so clear it after startup.
    with TestClient(app) as client:
        service.repo.threads.clear()
        response = client.post("/api/ask", json={"question": "What is happening?"})
        assert response.status_code == 409


def test_query_validation_and_missing_thread_analyze(service):
    app = create_app(service)
    with TestClient(app) as client:
        assert client.get("/api/work-items?page_size=101").status_code == 422
        assert client.post("/api/work-items/missing/analyze").status_code == 404


def test_thread_endpoint_returns_thread(service):
    service.ingest()
    thread_id = next(iter(service.repo.threads))
    app = create_app(service)
    with TestClient(app) as client:
        response = client.get(f"/api/threads/{thread_id}")
        assert response.status_code == 200
        assert response.json()["work_item"]["thread_id"] == thread_id


def test_ask_endpoint_maps_llm_and_thread_errors(service, monkeypatch):
    service.ingest()
    app = create_app(service)
    with TestClient(app) as client:
        missing = client.post("/api/ask", json={"question": "Tell me", "thread_id": "missing"})
        assert missing.status_code == 404
        from app.llm import LLMUnavailable
        monkeypatch.setattr(service.llm, "answer", lambda *args, **kwargs: (_ for _ in ()).throw(LLMUnavailable("offline")))
        thread_id = next(iter(service.repo.threads))
        failed = client.post("/api/ask", json={"question": "Tell me", "thread_id": thread_id})
        assert failed.status_code == 503


def test_invalid_filter_is_rejected(service):
    app = create_app(service)
    with TestClient(app) as client:
        assert client.get("/api/work-items?filter=unknown").status_code == 422
