from .llm import EmailLLM
from .mailbox import JsonMailboxSource, format_thread
from .models import EmailType, LLMDecision, Thread, WorkItem
from .prioritisation import classify_thread
from .repository import MailboxRepository


class IngestionService:
    """Turns source mailbox data into workload records."""

    def __init__(
        self,
        source: JsonMailboxSource,
        llm: EmailLLM,
        repo: MailboxRepository,
    ) -> None:
        self.source = source
        self.llm = llm
        self.repo = repo

    def ingest(
        self,
        only_threads: set[str] | None = None,
    ) -> dict[str, int]:
        """Process mailbox threads and return ingestion counts."""
        counts = self._empty_counts()

        for thread in self.source.read():
            thread_id = thread.messages[0].thread_id

            if only_threads is not None and thread_id not in only_threads:
                continue

            self._ingest_thread(thread_id, thread, only_threads)

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
        """Classify, build and persist one thread's workload record."""
        classified_type, _ = classify_thread(thread.messages)
        email_type = self.repo.type_overrides.get(thread_id, classified_type)
        existing_decision = self.repo.decisions.get(thread_id)

        decision = self._get_existing_decision(
            existing_decision,
            only_threads,
            email_type is EmailType.ACTION,
        )
        if email_type is not EmailType.ACTION:
            self.repo.invalidate_analysis(thread_id)

        work_item = self._build_work_item(
            thread_id=thread_id,
            thread=thread,
            email_type=email_type,
            decision=decision,
        )

        self.repo.upsert(thread, work_item, decision)

        if only_threads is not None:
            self.repo.invalidate_analysis(thread_id)

    @staticmethod
    def _get_existing_decision(
        decision: LLMDecision | None,
        only_threads: set[str] | None,
        actionable: bool,
    ) -> LLMDecision | None:
        """Keep existing AI analysis only for actionable threads."""
        if decision is not None and only_threads is None and actionable:
            return decision

        return None

    def _build_work_item(
        self,
        *,
        thread_id: str,
        thread: Thread,
        email_type,
        decision: LLMDecision | None,
    ) -> WorkItem:
        """Build a workload item from a mailbox thread."""
        latest = max(
            thread.messages,
            key=lambda message: message.date_sent,
        )

        return WorkItem(
            thread_id=thread_id,
            subject=latest.subject,
            latest_date=latest.date_sent,
            sender=latest.sent_from,
            email_type=email_type,
            topic=decision.topic if decision else None,
            actions=decision.actions if decision else [],
            urgency_signals=decision.urgency_signals if decision else [],
            importance_signals=decision.importance_signals if decision else [],
            priority=(
                self.repo.priority_overrides.get(thread_id, decision.priority)
                if decision
                else None
            ),
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
            done=(thread_id in self.repo.done_thread_ids) and email_type is EmailType.ACTION,
            in_progress=(thread_id in self.repo.in_progress_thread_ids) and email_type is EmailType.ACTION and thread_id not in self.repo.done_thread_ids,
            pinned=thread_id in self.repo.pinned_thread_ids,
        )

    @staticmethod
    def _empty_counts() -> dict[str, int]:
        """Return empty ingestion counters."""
        return {
            "threads_processed": 0,
            "messages_processed": 0,
            "action_items": 0,
            "informational_items": 0,
            "irrelevant_items": 0,
        }

    def analyze_thread(self, thread_id: str) -> LLMDecision:
        """Generate and store AI decision support for a thread."""
        thread = self.repo.get_thread(thread_id)

        if thread is None:
            raise KeyError(thread_id)

        if self.repo.work_items[thread_id].email_type.value != "action":
            raise ValueError("AI analysis is only available for actionable emails.")

        decision = self.llm.classify(format_thread(thread))
        self.repo.save_decision(thread_id, decision)

        return decision


class ContinuousIngestor:
    """Detects new messages and delegates processing to IngestionService."""

    def __init__(self, service: IngestionService) -> None:
        self.service = service
        self.seen_message_ids: set[str] = set()

    def prime(self) -> None:
        """Record existing messages before continuous polling starts."""
        self.seen_message_ids = {
            message.message_id
            for thread in self.service.source.read()
            for message in thread.messages
        }

    def poll(self) -> dict[str, int]:
        """Find new messages and process their affected threads."""
        threads = self.service.source.read()

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

        result = self.service.ingest(
            only_threads=changed_thread_ids,
        )

        self.seen_message_ids = {
            message.message_id
            for thread in threads
            for message in thread.messages
        }

        return result