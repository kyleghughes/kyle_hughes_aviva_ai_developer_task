from .audit import AuditLog
from .ingestion import IngestionService
from .llm import EmailLLM
from .mailbox import format_thread
from .models import AskRequest, AskResponse, WorkItem
from .prioritisation import RULE_VERSION
from .repository import MailboxRepository
from .retrieval import is_workload_question, retrieve, workload_evidence


class MailboxService:
    """Application use cases independent of FastAPI request handling."""

    def __init__(
        self,
        repo: MailboxRepository,
        ingestion: IngestionService,
        llm: EmailLLM,
        audit: AuditLog,
    ) -> None:
        self.repo = repo
        self.ingestion = ingestion
        self.llm = llm
        self.audit = audit

    def ingest(self) -> dict[str, int]:
        """Ingest the mailbox and record the ingestion event."""
        result = self.ingestion.ingest()

        self._audit(
            "mailbox_ingest",
            details=result,
        )

        return result

    def mark_done(
        self,
        thread_id: str,
        done: bool,
    ) -> WorkItem:
        """Mark a workload item as done or reopen it."""
        if self.repo.get_work_item(thread_id) is None:
            raise KeyError(thread_id)

        item = self.repo.set_done(
            thread_id,
            done,
        )

        self._audit(
            "work_item_done" if done else "work_item_reopened",
            thread_id=thread_id,
            details={"done": done},
        )

        return item

    def analyze(self, thread_id: str):
        """Generate AI decision support and update the workload item."""
        if self.repo.get_thread(thread_id) is None:
            raise KeyError(thread_id)

        decision = self.ingestion.analyze_thread(thread_id)
        item = self.repo.get_work_item(thread_id)

        self._audit(
            "llm_analysis",
            thread_id=thread_id,
            details={
                "work_type": item.email_type.value,
                "confidence": decision.confidence,
            },
        )

        return decision, item

    def ask(self, request: AskRequest) -> AskResponse:
        """Answer a mailbox question using the appropriate evidence."""
        if not self.repo.threads:
            raise RuntimeError(
                "Ingest the mailbox before asking questions.",
            )

        if request.thread_id:
            ids, evidence, mode = self._thread_evidence(
                request.thread_id,
            )
        elif is_workload_question(request.question):
            ids, evidence = workload_evidence(self.repo)
            mode = "workload"
        else:
            ids = retrieve(
                self.repo,
                request.question,
            )

            if not ids:
                return AskResponse(
                    answer=(
                        "That question isn't related to the mailbox "
                        "information I have available."
                    ),
                    thread_ids=[],
                    caveats=[
                        "No mailbox threads matched the question.",
                    ],
                    suggested_questions=[],
                )

            evidence = self._format_threads(ids)
            mode = "thread_search"

        result = self.llm.answer(
            request.question,
            evidence,
            mode=mode,
            history=[
                message.model_dump()
                for message in request.history
            ],
        )

        self._audit(
            "question_answered",
            details={
                "thread_ids": ids,
                "mode": mode,
            },
        )

        return AskResponse(
            answer=result["answer"],
            thread_ids=ids,
            caveats=[self._question_caveat(mode)],
            suggested_questions=result.get(
                "suggested_questions",
                [],
            ),
        )

    def _thread_evidence(
        self,
        thread_id: str,
    ) -> tuple[list[str], str, str]:
        """Build evidence for a question about one thread."""
        thread = self.repo.get_thread(thread_id)

        if thread is None:
            raise KeyError(thread_id)

        evidence = (
            f"THREAD {thread_id}\n"
            f"{format_thread(thread)}"
        )

        return [thread_id], evidence, "thread_search"

    def _format_threads(self, thread_ids: list[str]) -> str:
        """Format retrieved threads as LLM evidence."""
        return "\n\n".join(
            f"THREAD {thread_id}\n"
            f"{format_thread(self.repo.threads[thread_id])}"
            for thread_id in thread_ids
        )

    @staticmethod
    def _question_caveat(mode: str) -> str:
        """Return the evidence limitation for a Q&A mode."""
        if mode == "workload":
            return (
                "Work type is deterministic business logic; urgency and "
                "importance are decision-support signals from AI analysis "
                "when available."
            )

        return "Answer is generated from retrieved mailbox evidence only."

    def _audit(
        self,
        event_type: str,
        *,
        thread_id: str | None = None,
        details: dict,
    ) -> None:
        """Record an auditable application event."""
        self.audit.record(
            event_type,
            thread_id=thread_id,
            model=self.llm.model,
            rule_version=RULE_VERSION,
            details=details,
        )