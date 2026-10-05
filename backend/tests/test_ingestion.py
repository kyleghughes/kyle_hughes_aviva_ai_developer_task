from datetime import datetime, timezone

import pytest

from app.ingestion import ContinuousIngestor
from app.models import LLMDecision


def test_ingest_indexes_threads_and_preserves_done_state(ingested_service):
    assert len(ingested_service.repo.threads) == 50
    first = next(iter(ingested_service.repo.work_items))
    ingested_service.repo.set_done(first, True)
    ingested_service.ingestion.ingest()
    assert ingested_service.repo.work_items[first].done


def test_analyze_thread_updates_repository(ingested_service, monkeypatch):
    first = next(iter(ingested_service.repo.work_items))
    decision = LLMDecision(topic="claim", summary="Summary", rationale="Evidence", confidence=.9)
    monkeypatch.setattr(ingested_service.llm, "classify", lambda _: decision)
    result = ingested_service.ingestion.analyze_thread(first)
    assert result == decision
    assert ingested_service.repo.work_items[first].analysis_status == "analyzed"


def test_analyze_missing_thread_raises(ingested_service):
    with pytest.raises(KeyError):
        ingested_service.ingestion.analyze_thread("missing")


def test_poller_returns_zero_when_no_new_messages(poller):
    result = poller.poll()
    assert result["threads_processed"] == 0


def test_poller_processes_changed_threads(ingested_service, monkeypatch):
    poller = ContinuousIngestor(ingested_service.ingestion)
    poller.seen_message_ids = set()
    result = poller.poll()
    assert result["threads_processed"] == 50
    assert poller.seen_message_ids
