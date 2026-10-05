from .models import LLMDecision, Thread, WorkItem


class MailboxRepository:
    """In-memory application state with no business or HTTP logic."""

    def __init__(self) -> None:
        """Initialise the mailbox state stores."""
        self.work_items: dict[str, WorkItem] = {}
        self.threads: dict[str, Thread] = {}
        self.decisions: dict[str, LLMDecision] = {}
        self.done_thread_ids: set[str] = set()

    def upsert(
        self,
        thread: Thread,
        item: WorkItem,
        decision: LLMDecision | None = None,
    ) -> None:
        """Store a thread, its workload item and optional AI decision."""
        thread_id = thread.messages[0].thread_id

        self.threads[thread_id] = thread

        if decision is not None:
            self.decisions[thread_id] = decision

        self.work_items[thread_id] = item

    def get_thread(self, thread_id: str) -> Thread | None:
        """Return a stored thread by ID."""
        return self.threads.get(thread_id)

    def get_work_item(self, thread_id: str) -> WorkItem | None:
        """Return a stored workload item by thread ID."""
        return self.work_items.get(thread_id)

    def set_done(
        self,
        thread_id: str,
        done: bool,
    ) -> WorkItem:
        """Update the completed state of a workload item."""
        item = self.work_items[thread_id]

        if done:
            self.done_thread_ids.add(thread_id)
        else:
            self.done_thread_ids.discard(thread_id)

        updated = item.model_copy(
            update={"done": done},
        )

        self.work_items[thread_id] = updated

        return updated

    def save_decision(
        self,
        thread_id: str,
        decision: LLMDecision,
    ) -> WorkItem:
        """Store AI analysis and update the corresponding workload item."""
        self.decisions[thread_id] = decision

        item = self.work_items[thread_id]

        updated = item.model_copy(
            update={
                "topic": decision.topic,
                "actions": decision.actions,
                "urgency_signals": decision.urgency_signals,
                "importance_signals": decision.importance_signals,
                "summary": decision.summary,
                "confidence": decision.confidence,
                "analysis_status": "analyzed",
            },
        )

        self.work_items[thread_id] = updated

        return updated

    def invalidate_analysis(self, thread_id: str) -> None:
        """Remove stored AI analysis so the thread can be re-analysed."""
        self.decisions.pop(thread_id, None)