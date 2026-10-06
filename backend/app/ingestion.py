from .llm import EmailLLM
from .mailbox import JsonMailboxSource, format_thread
from .models import EmailType, LLMDecision, Thread, WorkItem
from .prioritisation import classify_thread
from .repository import MailboxRepository


class IngestionService:
    """Convert mailbox data into persisted workload records.

    Ingestion is responsible for deterministic email classification,
    preserving user overrides, rebuilding work items, and coordinating
    AI analysis when explicitly requested.
    """

    def __init__(
        self,
        source: JsonMailboxSource,
        llm: EmailLLM,
        repo: MailboxRepository,
    ) -> None:
        """Initialise the ingestion service and its dependencies."""
        self.source = source
        self.llm = llm
        self.repo = repo

    def ingest(
        self,
        only_threads: set[str] | None = None,
    ) -> dict[str, int]:
        """Process mailbox threads and return ingestion statistics.

        When ``only_threads`` is supplied, only those threads are
        reprocessed. This is used by continuous ingestion to avoid
        rebuilding unchanged mailbox records.
        """
        counts = self._empty_counts()

        for thread in self.source.read():
            thread_id = thread.messages[0].thread_id

            if only_threads is not None and thread_id not in only_threads:
                continue

            self._ingest_thread(
                thread_id,
                thread,
                only_threads,
            )

            email_type = self.repo.work_items[thread_id].email_type

            counts["threads_processed"] += 1
            counts["messages_processed"] += len(thread.messages)
            counts[f"{email_type.value}_items"] += 1

        return counts

    def _ingest_thread(
        self,
        thread_id: str,
        thread: Thread,
        only_threads: set[str] | None,
    ) -> None:
        """Classify and persist a single mailbox thread.

        Classification is deterministic. Existing user type overrides
        take precedence over the classifier. Existing AI analysis is
        preserved during a normal full ingestion, but is deliberately
        invalidated when a thread is being selectively reprocessed.
        """
        # Determine the email's underlying type using deterministic rules.
        classified_type, _ = classify_thread(thread.messages)

        # A user-selected type always takes precedence over classification.
        email_type = self.repo.type_overrides.get(
            thread_id,
            classified_type,
        )

        # Preserve existing AI analysis only when this is a normal
        # ingestion of an already analysed actionable thread.
        existing_decision = self.repo.decisions.get(thread_id)
        decision = self._get_existing_decision(
            existing_decision,
            only_threads,
            email_type is EmailType.ACTION,
        )

        # Archived/non-actionable threads must not retain AI analysis.
        if email_type is not EmailType.ACTION:
            self.repo.invalidate_analysis(thread_id)

        work_item = self._build_work_item(
            thread_id=thread_id,
            thread=thread,
            email_type=email_type,
            decision=decision,
        )

        self.repo.upsert(
            thread,
            work_item,
            decision,
        )

        # A selective re-ingestion represents a mailbox change. Clear
        # previous analysis so the updated actionable thread can be
        # analysed again when the user opens it.
        if only_threads is not None:
            self.repo.invalidate_analysis(thread_id)

    @staticmethod
    def _get_existing_decision(
        decision: LLMDecision | None,
        only_threads: set[str] | None,
        actionable: bool,
    ) -> LLMDecision | None:
        """Return reusable AI analysis when the thread is still actionable.

        Existing analysis is retained during a full ingestion, but not
        during selective reprocessing of changed threads.
        """
        if decision is not None and only_threads is None and actionable:
            return decision

        return None

    def _build_work_item(
        self,
        *,
        thread_id: str,
        thread: Thread,
        email_type: EmailType,
        decision: LLMDecision | None,
    ) -> WorkItem:
        """Build the workload representation for a mailbox thread.

        AI-derived fields are populated only when analysis is available.
        Otherwise the item remains explicitly marked as awaiting analysis.
        """
        # The latest message provides the current subject, sender,
        # timestamp, and importance flag shown in the workload.
        latest = max(
            thread.messages,
            key=lambda message: message.date_sent,
        )

        # A manually selected priority takes precedence over the
        # priority supplied by AI analysis.
        priority = (
            self.repo.priority_overrides.get(
                thread_id,
                decision.priority,
            )
            if decision
            else None
        )

        # Workflow state is only meaningful for actionable emails.
        is_actionable = email_type is EmailType.ACTION
        is_done = thread_id in self.repo.done_thread_ids
        is_in_progress = thread_id in self.repo.in_progress_thread_ids

        return WorkItem(
            thread_id=thread_id,
            subject=latest.subject,
            latest_date=latest.date_sent,
            sender=latest.sent_from,
            email_type=email_type,
            topic=decision.topic if decision else None,
            actions=decision.actions if decision else [],
            urgency_signals=(
                decision.urgency_signals
                if decision
                else []
            ),
            importance_signals=(
                decision.importance_signals
                if decision
                else []
            ),
            priority=priority,
            summary=(
                decision.summary
                if decision
                else "Awaiting AI analysis when opened."
            ),
            confidence=decision.confidence if decision else None,
            analysis_status=(
                "analyzed"
                if decision
                else "not_analyzed"
            ),
            message_count=len(thread.messages),
            importance_flag=latest.importance_flag,
            done=is_actionable and is_done,
            in_progress=(
                is_actionable
                and is_in_progress
                and not is_done
            ),
            pinned=thread_id in self.repo.pinned_thread_ids,
        )

    @staticmethod
    def _empty_counts() -> dict[str, int]:
        """Return a fresh set of zeroed ingestion counters."""
        return {
            "threads_processed": 0,
            "messages_processed": 0,
            "action_items": 0,
            "informational_items": 0,
            "irrelevant_items": 0,
        }

    def analyze_thread(self, thread_id: str) -> LLMDecision:
        """Run AI analysis for an actionable thread and persist the result.

        AI analysis is intentionally separate from deterministic ingestion.
        A thread is analysed only when explicitly requested and only when
        its current email type is actionable.
        """
        thread = self.repo.get_thread(thread_id)

        if thread is None:
            raise KeyError(thread_id)

        if self.repo.work_items[thread_id].email_type.value != "action":
            raise ValueError(
                "AI analysis is only available for actionable emails."
            )

        decision = self.llm.classify(format_thread(thread))
        self.repo.save_decision(thread_id, decision)

        return decision


class ContinuousIngestor:
    """Detect new mailbox messages and reprocess affected threads."""

    def __init__(self, service: IngestionService) -> None:
        """Initialise the continuous ingestor."""
        self.service = service
        self.seen_message_ids: set[str] = set()

    def prime(self) -> None:
        """Record the current mailbox state before polling begins.

        Existing messages are treated as already known so that the first
        poll only processes messages that arrive afterwards.
        """
        self.seen_message_ids = {
            message.message_id
            for thread in self.service.source.read()
            for message in thread.messages
        }

    def poll(self) -> dict[str, int]:
        """Detect new messages and reprocess their affected threads.

        A thread is re-ingested when at least one of its messages has not
        been seen previously. If nothing has changed, zeroed counters are
        returned without performing unnecessary ingestion work.
        """
        threads = self.service.source.read()

        # Identify every thread containing at least one new message.
        changed_thread_ids = {
            thread.messages[0].thread_id
            for thread in threads
            if any(
                message.message_id not in self.seen_message_ids
                for message in thread.messages
            )
        }

        if not changed_thread_ids:
            return self.service._empty_counts()

        # Reprocess only the threads affected by newly arrived messages.
        result = self.service.ingest(
            only_threads=changed_thread_ids,
        )

        # Refresh the known-message set after successful processing so
        # the same messages are not repeatedly treated as new.
        self.seen_message_ids = {
            message.message_id
            for thread in threads
            for message in thread.messages
        }

        return result