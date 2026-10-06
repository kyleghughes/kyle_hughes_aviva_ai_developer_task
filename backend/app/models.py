from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EmailType(str, Enum):
    """Deterministic classification used to route emails through the workflow."""

    ACTION = "action"
    INFORMATIONAL = "informational"
    IRRELEVANT = "irrelevant"


class Priority(str, Enum):
    """Priority assigned to actionable work by AI or a user override."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Attachment(BaseModel):
    """Metadata describing an email attachment."""

    filename: str
    filesize: int
    filetype: str


class Email(BaseModel):
    """Represents a single message received or sent through the mailbox."""

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
    """Represents a conversation made up of related email messages."""

    messages: list[Email]


class LLMDecision(BaseModel):
    """AI decision-support output produced when an actionable thread is analysed."""

    topic: str

    # Actions explicitly requested or clearly required by the email thread.
    actions: list[str] = Field(default_factory=list)

    # Evidence indicating why the thread may require urgent attention.
    urgency_signals: list[str] = Field(default_factory=list)

    # Evidence indicating why the thread is important to the business/customer.
    importance_signals: list[str] = Field(default_factory=list)

    # AI-assessed workload priority.
    priority: Priority

    # Concise explanation of what the thread is about and why it matters.
    summary: str

    # Model confidence is constrained to a normalised 0-1 range.
    confidence: float = Field(ge=0, le=1)

    # Supporting explanation for the AI's assessment.
    rationale: str


class WorkItem(BaseModel):
    """Workload representation used to display and manage a mailbox thread."""

    thread_id: str
    subject: str
    latest_date: datetime
    sender: str

    # Deterministic workflow classification.
    email_type: EmailType

    # AI-derived fields are populated after an actionable thread is analysed.
    topic: str | None = None
    actions: list[str] = Field(default_factory=list)
    urgency_signals: list[str] = Field(default_factory=list)
    importance_signals: list[str] = Field(default_factory=list)
    priority: Priority | None = None

    summary: str = "Awaiting AI analysis when opened."
    confidence: float | None = None
    analysis_status: str = "not_analyzed"

    # Mailbox metadata used by the workload view.
    message_count: int
    importance_flag: str | None = None

    # User-controlled workflow state.
    done: bool = False
    in_progress: bool = False
    pinned: bool = False


class WorkTypeUpdate(BaseModel):
    """Request to override an email's deterministic workflow classification."""

    email_type: EmailType


class PriorityUpdate(BaseModel):
    """Request to override the AI-assessed priority of an actionable thread."""

    priority: Priority


class IngestResponse(BaseModel):
    """Counts returned after a mailbox ingestion operation."""

    threads_processed: int
    messages_processed: int
    action_items: int
    informational_items: int
    irrelevant_items: int


class ChatMessage(BaseModel):
    """Single message in a natural-language mailbox Q&A conversation."""

    role: str
    content: str = Field(
        min_length=1,
        max_length=4000,
    )


class AskRequest(BaseModel):
    """Request containing a user's natural-language mailbox question."""

    question: str = Field(
        min_length=3,
        max_length=1000,
    )

    # Optional thread context for questions focused on one conversation.
    thread_id: str | None = None

    # Previous Q&A messages supplied as conversational context.
    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=20,
    )


class AskResponse(BaseModel):
    """Structured response returned by the mailbox Q&A service."""

    answer: str

    # Internal thread IDs used by the application to identify relevant work.
    thread_ids: list[str]

    # Human-readable titles corresponding to the returned thread IDs.
    thread_titles: dict[str, str] = Field(default_factory=dict)

    # Any limitations or qualifications that should be shown to the user.
    caveats: list[str] = Field(default_factory=list)

    # Grounded follow-up questions suggested by the assistant.
    suggested_questions: list[str] = Field(
        default_factory=list,
        max_length=4,
    )


class AuditEvent(BaseModel):
    """Auditable record of an application event or AI-assisted decision."""

    timestamp: datetime
    event_type: str
    thread_id: str | None = None
    model: str | None = None
    rule_version: str | None = None
    details: dict