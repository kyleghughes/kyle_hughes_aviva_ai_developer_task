from pathlib import Path

import pytest

from app.audit import AuditLog
from app.ingestion import IngestionService, ContinuousIngestor
from app.llm import EmailLLM
from app.mailbox import JsonMailboxSource
from app.repository import MailboxRepository
from app.services import MailboxService


@pytest.fixture
def mailbox_path() -> Path:
    return Path(__file__).resolve().parents[1] / "emails_candidate.json"


@pytest.fixture
def repository() -> MailboxRepository:
    return MailboxRepository()


@pytest.fixture
def source(mailbox_path: Path) -> JsonMailboxSource:
    return JsonMailboxSource(mailbox_path)


@pytest.fixture
def llm(monkeypatch: pytest.MonkeyPatch) -> EmailLLM:
    monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")
    return EmailLLM()


@pytest.fixture
def service(source, repository, llm) -> MailboxService:
    ingestion = IngestionService(source, llm, repository)
    return MailboxService(repository, ingestion, llm, AuditLog())


@pytest.fixture
def ingested_service(service: MailboxService) -> MailboxService:
    service.ingest()
    return service


@pytest.fixture
def poller(ingested_service: MailboxService) -> ContinuousIngestor:
    poller = ContinuousIngestor(ingested_service.ingestion)
    poller.prime()
    return poller
