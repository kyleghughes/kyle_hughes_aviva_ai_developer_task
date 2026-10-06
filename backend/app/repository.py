from .models import EmailType, LLMDecision, Priority, Thread, WorkItem


class MailboxRepository:
    """In-memory store for mailbox data and user workflow state.

    The repository deliberately contains no HTTP or business-classification
    logic. It provides a central place to persist threads, workload items,
    AI decisions, and user-selected overrides during the application's
    lifetime.
    """

    def __init__(self) -> None:
        """Initialise the mailbox state stores."""

        # Core mailbox data and derived workload records.
        self.work_items: dict[str, WorkItem] = {}
        self.threads: dict[str, Thread] = {}

        # AI analysis keyed by thread ID.
        self.decisions: dict[str, LLMDecision] = {}

        # User-controlled workflow state.
        self.done_thread_ids: set[str] = set()
        self.in_progress_thread_ids: set[str] = set()
        self.pinned_thread_ids: set[str] = set()

        # Manual overrides take precedence over automatically derived values.
        self.type_overrides: dict[str, EmailType] = {}
        self.priority_overrides: dict[str, Priority] = {}

    def upsert(
        self,
        thread: Thread,
        item: WorkItem,
        decision: LLMDecision | None = None,
    ) -> None:
        """Store a thread, its workload item, and optional AI analysis."""
        thread_id = thread.messages[0].thread_id

        self.threads[thread_id] = thread

        if decision is not None:
            self.decisions[thread_id] = decision

        self.work_items[thread_id] = item

    def get_thread(self, thread_id: str) -> Thread | None:
        """Return a stored email thread by ID, if it exists."""
        return self.threads.get(thread_id)

    def get_work_item(self, thread_id: str) -> WorkItem | None:
        """Return a stored workload item by thread ID, if it exists."""
        return self.work_items.get(thread_id)

    def set_in_progress(
        self,
        thread_id: str,
        in_progress: bool,
    ) -> WorkItem:
        """Start or stop work on an actionable item.

        An actioned item cannot be placed directly back into progress;
        it must first be reopened.
        """
        item = self.work_items[thread_id]

        if item.email_type is not EmailType.ACTION:
            raise ValueError(
                "Only actionable emails can be put in progress."
            )

        if item.done and in_progress:
            raise ValueError(
                "An actioned item must be reopened before it can be put in progress."
            )

        if in_progress:
            self.in_progress_thread_ids.add(thread_id)
        else:
            self.in_progress_thread_ids.discard(thread_id)

        updated = item.model_copy(
            update={"in_progress": in_progress},
        )
        self.work_items[thread_id] = updated

        return updated

    def set_done(
        self,
        thread_id: str,
        done: bool,
    ) -> WorkItem:
        """Mark an actionable item as actioned or reopen it.

        Completing work is deliberately gated behind the In Progress
        state so the workflow follows:

        Actionable → In Progress → Actioned
        """
        item = self.work_items[thread_id]

        if done and not item.in_progress:
            raise ValueError(
                "A work item must be in progress before it can be actioned."
            )

        if done and item.email_type is not EmailType.ACTION:
            raise ValueError(
                "Only actionable emails can be marked actioned."
            )

        if done:
            self.done_thread_ids.add(thread_id)
        else:
            self.done_thread_ids.discard(thread_id)
            self.in_progress_thread_ids.add(thread_id)

        updated = item.model_copy(
            update={
                "done": done,
                "in_progress": False if done else True,
            },
        )

        # An actioned item is no longer considered in progress.
        if done:
            self.in_progress_thread_ids.discard(thread_id)

        self.work_items[thread_id] = updated

        return updated

    def set_pinned(
        self,
        thread_id: str,
        pinned: bool,
    ) -> WorkItem:
        """Pin or unpin a thread for quick access in workload views."""
        item = self.work_items[thread_id]

        if pinned:
            self.pinned_thread_ids.add(thread_id)
        else:
            self.pinned_thread_ids.discard(thread_id)

        updated = item.model_copy(
            update={"pinned": pinned},
        )
        self.work_items[thread_id] = updated

        return updated

    def save_decision(
        self,
        thread_id: str,
        decision: LLMDecision,
    ) -> WorkItem:
        """Store AI analysis and apply it to the corresponding work item.

        A manually selected priority is preserved when present; otherwise
        the priority supplied by the latest AI analysis is used.
        """
        self.decisions[thread_id] = decision

        item = self.work_items[thread_id]

        updated = item.model_copy(
            update={
                "topic": decision.topic,
                "actions": decision.actions,
                "urgency_signals": decision.urgency_signals,
                "importance_signals": decision.importance_signals,
                "priority": self.priority_overrides.get(
                    thread_id,
                    decision.priority,
                ),
                "summary": decision.summary,
                "confidence": decision.confidence,
                "analysis_status": "analyzed",
            },
        )

        self.work_items[thread_id] = updated

        return updated

    def invalidate_analysis(self, thread_id: str) -> None:
        """Remove stored AI analysis and its priority override.

        This is used when a thread changes or moves back into the
        actionable workflow and therefore needs fresh analysis.
        """
        self.decisions.pop(thread_id, None)
        self.priority_overrides.pop(thread_id, None)

    def set_priority(
        self,
        thread_id: str,
        priority: Priority,
    ) -> WorkItem:
        """Store a user-selected priority override for a work item."""
        item = self.work_items[thread_id]

        self.priority_overrides[thread_id] = priority

        updated = item.model_copy(
            update={"priority": priority},
        )
        self.work_items[thread_id] = updated

        return updated

    def set_email_type(
        self,
        thread_id: str,
        email_type: EmailType,
    ) -> WorkItem:
        """Store a user-selected workflow category override.

        Moving an actionable item into an archived category also clears
        its active workflow state because only actionable emails can be
        In Progress or Actioned.
        """
        item = self.work_items[thread_id]

        self.type_overrides[thread_id] = email_type

        # Non-actionable items cannot remain actioned or in progress.
        done = (
            item.done
            if email_type is EmailType.ACTION
            else False
        )
        in_progress = (
            item.in_progress
            if email_type is EmailType.ACTION
            else False
        )

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