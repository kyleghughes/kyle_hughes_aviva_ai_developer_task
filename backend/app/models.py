from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EmailType(str, Enum):
    """Deterministic mailbox workflow classification."""

    ACTION = "action"
    INFORMATIONAL = "informational"
    IRRELEVANT = "irrelevant"


class Attachment(BaseModel):
    """Email attachment metadata."""

    filename: str
    filesize: int
    filetype: str


class Email(BaseModel):
    """Represents a single mailbox message."""

    body: str
    subject: str
    sent_from: str
    sent_to: list[str]
    sent_cc: list[str] | None = None
    date_sent: datetime
    attachments: list[Attachment] | None = None
    importance_flag: str | None = None
    message_id: str
    thread_id: str


class Thread(BaseModel):
    """Represents a conversation containing related emails."""

    messages: list[Email]


class LLMDecision(BaseModel):
    """AI decision-support output for a mailbox thread."""

    topic: str
    actions: list[str] = Field(default_factory=list)
    urgency_signals: list[str] = Field(default_factory=list)
    importance_signals: list[str] = Field(default_factory=list)
    summary: str
    confidence: float = Field(ge=0, le=1)
    rationale: str


class WorkItem(BaseModel):
    """Workload representation used by the application UI."""

    thread_id: str
    subject: str
    latest_date: datetime
    sender: str
    email_type: EmailType
    topic: str | None = None
    actions: list[str] = Field(default_factory=list)
    urgency_signals: list[str] = Field(default_factory=list)
    importance_signals: list[str] = Field(default_factory=list)
    summary: str = "Awaiting AI analysis when opened."
    confidence: float | None = None
    analysis_status: str = "not_analyzed"
    message_count: int
    importance_flag: str | None = None
    done: bool = False


class IngestResponse(BaseModel):
    """Result returned after mailbox ingestion."""

    threads_processed: int
    messages_processed: int
    action_items: int
    informational_items: int
    irrelevant_items: int


class ChatMessage(BaseModel):
    """Single message in a mailbox Q&A conversation."""

    role: str
    content: str = Field(
        min_length=1,
        max_length=4000,
    )


class AskRequest(BaseModel):
    """Request for a natural-language mailbox question."""

    question: str = Field(
        min_length=3,
        max_length=1000,
    )
    thread_id: str | None = None
    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=20,
    )


class AskResponse(BaseModel):
    """Response returned from mailbox Q&A."""

    answer: str
    thread_ids: list[str]
    caveats: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(
        default_factory=list,
        max_length=4,
    )


class AuditEvent(BaseModel):
    """Auditable record of an application or AI event."""

    timestamp: datetime
    event_type: str
    thread_id: str | None = None
    model: str | None = None
    rule_version: str | None = None
    details: dict