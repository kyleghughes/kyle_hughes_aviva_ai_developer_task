from .models import EmailType, LLMDecision, Priority, Thread, WorkItem


class MailboxRepository:
    """In-memory application state with no business or HTTP logic."""

    def __init__(self) -> None:
        """Initialise the mailbox state stores."""
        self.work_items: dict[str, WorkItem] = {}
        self.threads: dict[str, Thread] = {}
        self.decisions: dict[str, LLMDecision] = {}
        self.done_thread_ids: set[str] = set()
        self.in_progress_thread_ids: set[str] = set()
        self.pinned_thread_ids: set[str] = set()
        self.type_overrides: dict[str, EmailType] = {}
        self.priority_overrides: dict[str, Priority] = {}

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

    def set_in_progress(self, thread_id: str, in_progress: bool) -> WorkItem:
        """Start or stop work on an actionable item."""
        item = self.work_items[thread_id]
        if item.email_type is not EmailType.ACTION:
            raise ValueError("Only actionable emails can be put in progress.")
        if item.done and in_progress:
            raise ValueError("An actioned item must be reopened before it can be put in progress.")

        if in_progress:
            self.in_progress_thread_ids.add(thread_id)
        else:
            self.in_progress_thread_ids.discard(thread_id)

        updated = item.model_copy(update={"in_progress": in_progress})
        self.work_items[thread_id] = updated
        return updated

    def set_done(
        self,
        thread_id: str,
        done: bool,
    ) -> WorkItem:
        """Update the completed state of a workload item."""
        item = self.work_items[thread_id]

        if done and not item.in_progress:
            raise ValueError("A work item must be in progress before it can be actioned.")
        if done and item.email_type is not EmailType.ACTION:
            raise ValueError("Only actionable emails can be marked actioned.")

        if done:
            self.done_thread_ids.add(thread_id)
        else:
            self.done_thread_ids.discard(thread_id)

        if not done:
            self.in_progress_thread_ids.add(thread_id)
        updated = item.model_copy(
            update={"done": done, "in_progress": False if done else True},
        )
        if done:
            self.in_progress_thread_ids.discard(thread_id)

        self.work_items[thread_id] = updated

        return updated


    def set_pinned(self, thread_id: str, pinned: bool) -> WorkItem:
        """Pin or unpin a thread for quick access in workload views."""
        item = self.work_items[thread_id]

        if pinned:
            self.pinned_thread_ids.add(thread_id)
        else:
            self.pinned_thread_ids.discard(thread_id)

        updated = item.model_copy(update={"pinned": pinned})
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
                "priority": self.priority_overrides.get(thread_id, decision.priority),
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
        self.priority_overrides.pop(thread_id, None)

    def set_priority(self, thread_id: str, priority: Priority) -> WorkItem:
        """Set a user-selected priority override."""
        item = self.work_items[thread_id]
        self.priority_overrides[thread_id] = priority
        updated = item.model_copy(update={"priority": priority})
        self.work_items[thread_id] = updated
        return updated

    def set_email_type(self, thread_id: str, email_type: EmailType) -> WorkItem:
        """Set a user-selected workflow category override."""
        item = self.work_items[thread_id]
        self.type_overrides[thread_id] = email_type

        # A non-actionable item cannot remain actioned.
        done = item.done if email_type is EmailType.ACTION else False
        in_progress = item.in_progress if email_type is EmailType.ACTION else False
        if email_type is not EmailType.ACTION:
            self.in_progress_thread_ids.discard(thread_id)
        if not done:
            self.done_thread_ids.discard(thread_id)

        updated = item.model_copy(
            update={
                "email_type": email_type,
                "done": done,
                "in_progress": in_progress,
            },
        )
        self.work_items[thread_id] = updated
        return updated
