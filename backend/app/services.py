from .audit import AuditLog
from .ingestion import IngestionService
from .llm import EmailLLM
from .mailbox import format_thread
from .models import AskRequest, AskResponse, EmailType, Priority, WorkItem
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

    def mark_in_progress(self, thread_id: str, in_progress: bool = True) -> WorkItem:
        """Start work on an actionable item or stop an in-progress state."""
        item = self.repo.get_work_item(thread_id)
        if item is None:
            raise KeyError(thread_id)
        updated = self.repo.set_in_progress(thread_id, in_progress)
        self._audit(
            "work_item_in_progress" if in_progress else "work_item_no_longer_in_progress",
            thread_id=thread_id,
            details={"in_progress": in_progress},
        )
        return updated

    def mark_done(
        self,
        thread_id: str,
        done: bool,
    ) -> WorkItem:
        """Mark a workload item as done or reopen it."""
        if self.repo.get_work_item(thread_id) is None:
            raise KeyError(thread_id)

        if self.repo.work_items[thread_id].email_type is not EmailType.ACTION:
            raise ValueError("Only actionable emails can change work status.")
        if done and not self.repo.work_items[thread_id].in_progress:
            raise ValueError("A work item must be in progress before it can be actioned.")

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

    def set_pinned(self, thread_id: str, pinned: bool) -> WorkItem:
        """Pin or unpin a thread."""
        if self.repo.get_work_item(thread_id) is None:
            raise KeyError(thread_id)

        item = self.repo.set_pinned(thread_id, pinned)
        self._audit(
            "work_item_pinned" if pinned else "work_item_unpinned",
            thread_id=thread_id,
            details={"pinned": pinned},
        )
        return item

    def set_priority(self, thread_id: str, priority: Priority) -> WorkItem:
        """Apply a manual priority override after AI analysis."""
        item = self.repo.get_work_item(thread_id)
        if item is None:
            raise KeyError(thread_id)
        if item.email_type is not EmailType.ACTION:
            raise ValueError("Priority is only available for actionable emails.")
        if item.analysis_status != "analyzed":
            raise ValueError("AI analysis must be complete before priority can be overridden.")

        previous = item.priority
        updated = self.repo.set_priority(thread_id, priority)
        self._audit(
            "work_item_priority_changed",
            thread_id=thread_id,
            details={"from": previous.value if previous else None, "to": priority.value, "manual_override": True},
        )
        return updated

    def set_email_type(self, thread_id: str, email_type: EmailType) -> WorkItem:
        """Apply a user-selected workflow category override."""
        if self.repo.get_work_item(thread_id) is None:
            raise KeyError(thread_id)

        previous = self.repo.work_items[thread_id].email_type
        item = self.repo.set_email_type(thread_id, email_type)

        # Category changes invalidate decision support in both directions.
        # Moving away from actionable makes the thread archive-only; moving
        # back to actionable must force a fresh AI assessment and priority.
        self.repo.invalidate_analysis(thread_id)
        if email_type is not EmailType.ACTION:
            item = self.repo.work_items[thread_id].model_copy(
                update={
                    "topic": None,
                    "actions": [],
                    "urgency_signals": [],
                    "importance_signals": [],
                    "priority": None,
                    "summary": "Archived email — conversation only.",
                    "confidence": None,
                    "analysis_status": "not_analyzed",
                },
            )
        else:
            item = self.repo.work_items[thread_id].model_copy(
                update={
                    "topic": None,
                    "actions": [],
                    "urgency_signals": [],
                    "importance_signals": [],
                    "priority": None,
                    "summary": "Awaiting AI analysis when opened.",
                    "confidence": None,
                    "analysis_status": "not_analyzed",
                },
            )
        self.repo.work_items[thread_id] = item

        self._audit(
            "work_item_type_changed",
            thread_id=thread_id,
            details={"from": previous.value, "to": email_type.value},
        )
        return item

    def analyze(self, thread_id: str):
        """Generate AI decision support and update the workload item."""
        if self.repo.get_thread(thread_id) is None:
            raise KeyError(thread_id)
        item = self.repo.get_work_item(thread_id)
        if item is not None and item.email_type.value != "action":
            raise ValueError("AI analysis is only available for actionable emails.")

        decision = self.ingestion.analyze_thread(thread_id)
        item = self.repo.get_work_item(thread_id)

        self._audit(
            "llm_analysis",
            thread_id=thread_id,
            details={
                "work_type": item.email_type.value,
                "confidence": decision.confidence,
                "priority": decision.priority.value,
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
            ids, evidence = workload_evidence(self.repo, question=request.question)
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
                    thread_titles={},
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
            thread_titles={
                thread_id: self.repo.work_items[thread_id].subject
                for thread_id in ids
                if thread_id in self.repo.work_items
            },
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

        title = self.repo.work_items[thread_id].subject if thread_id in self.repo.work_items else thread.messages[-1].subject
        evidence = (
            f"WORK ITEM TITLE: {title}\n"
            f"{format_thread(thread)}"
        )

        return [thread_id], evidence, "thread_search"

    def _format_threads(self, thread_ids: list[str]) -> str:
        """Format retrieved threads as LLM evidence."""
        return "\n\n".join(
            f"WORK ITEM TITLE: {self.repo.work_items[thread_id].subject if thread_id in self.repo.work_items else self.repo.threads[thread_id].messages[-1].subject}\n"
            f"{format_thread(self.repo.threads[thread_id])}"
            for thread_id in thread_ids
        )

    @staticmethod
    def _question_caveat(mode: str) -> str:
        """Return the evidence limitation for a Q&A mode."""
        if mode == "workload":
            return (
                "Work type is deterministic business logic; priority, urgency "
                "and importance are AI decision-support assessments when "
                "available."
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