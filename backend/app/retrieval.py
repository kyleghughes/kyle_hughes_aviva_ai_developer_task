import os
import re

from .mailbox import format_thread
from .models import EmailType, WorkItem
from .prioritisation import sort_work_items
from .repository import MailboxRepository


# Words that usually describe the question rather than the mailbox content.
# Removing them leaves more meaningful terms for simple retrieval matching.
QUERY_STOPWORDS = {
    "what",
    "when",
    "where",
    "which",
    "who",
    "whom",
    "whose",
    "how",
    "does",
    "did",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "has",
    "have",
    "had",
    "can",
    "could",
    "would",
    "should",
    "will",
    "the",
    "and",
    "for",
    "with",
    "from",
    "about",
    "this",
    "that",
    "there",
    "their",
    "they",
    "them",
    "you",
    "your",
    "please",
    "tell",
    "any",
    "some",
    "into",
    "not",
    "email",
    "emails",
    "mailbox",
    "question",
    "colour",
    "color",
    "i",
    "me",
    "my",
    "we",
    "our",
    "to",
    "a",
    "an",
    "of",
    "on",
    "in",
    "at",
    "or",
    "it",
    "now",
}


# Common natural-language questions that clearly ask about current workload.
WORKLOAD_PATTERNS = (
    "what should i prioritise",
    "what should i prioritize",
    "what do i prioritise",
    "what do i prioritize",
    "what needs my attention",
    "what needs attention",
    "what is most urgent",
    "what's most urgent",
    "which is most urgent",
    "which are most urgent",
    "what should i deal with first",
    "what should i handle first",
    "what should i work on first",
    "what should i focus on",
    "where should i focus",
    "what are my priorities",
    "what is my priority",
    "what's my priority",
    "which emails should i prioritise",
    "which emails should i prioritize",
    "which emails need attention",
    "which emails are urgent",
    "show me my priorities",
    "show my priorities",
    "what is urgent",
    "what's urgent",
    "are there any messages that look urgent",
    "are there any emails that look urgent",
    "which emails require a response",
    "which emails need a response",
    "which messages require a response",
    "which messages need a response",
    "what emails require a response",
    "what emails need a response",
    "what messages require a response",
    "what messages need a response",
    "who needs a response",
    "which emails need responding to",
    "which messages need responding to",
    "what needs doing",
)


def is_workload_question(question: str) -> bool:
    """Return whether a question is asking about current workload.

    Detection is intentionally deterministic. It is used to decide which
    mailbox evidence should be supplied to the LLM, rather than asking the
    LLM to decide how the application's workload should be interpreted.
    """
    normalised = re.sub(
        r"[^a-z0-9' ]+",
        " ",
        question.lower(),
    ).strip()

    # Match common workload questions directly.
    if any(
        pattern in normalised
        for pattern in WORKLOAD_PATTERNS
    ):
        return True

    # Also recognise less predictable wording when it contains both a
    # workload concept and an indication that the user wants to act on it.
    workload_terms = {
        "prioritise",
        "prioritize",
        "priority",
        "priorities",
        "urgent",
        "attention",
        "workload",
        "queue",
        "focus",
    }

    action_terms = {
        "should",
        "need",
        "needs",
        "handle",
        "deal",
        "work",
        "do",
        "focus",
        "first",
    }

    tokens = set(
        re.findall(r"[a-z]+", normalised),
    )

    return bool(tokens & workload_terms) and bool(tokens & action_terms)


def retrieve(
    repo: MailboxRepository,
    question: str,
    limit: int = 8,
) -> list[str]:
    """Return the most relevant threads using simple term matching.

    Each non-stopword term contributes one point for every occurrence in
    the formatted thread. Results are then ordered by descending score
    with the thread ID providing a deterministic tie-breaker.
    """
    terms = {
        token.lower()
        for token in re.findall(
            r"[A-Za-z0-9][A-Za-z0-9\_-]{2,}",
            question,
        )
        if token.lower() not in QUERY_STOPWORDS
    }

    if not terms:
        return []

    scored: list[tuple[int, str]] = []

    for thread_id, thread in repo.threads.items():
        text = format_thread(thread).lower()
        score = sum(
            text.count(term)
            for term in terms
        )

        if score:
            scored.append((score, thread_id))

    # Highest relevance first; thread ID makes equal scores deterministic.
    scored.sort(
        key=lambda value: (-value[0], value[1]),
    )

    return [
        thread_id
        for _, thread_id in scored[:limit]
    ]


def workload_evidence(
    repo: MailboxRepository,
    question: str | None = None,
    limit: int = 12,
) -> tuple[list[str], str]:
    """Build focused evidence from the current open actionable workload.

    Informational, irrelevant, and actioned threads are excluded. The
    remaining items are ordered according to the user's question when it
    asks specifically about responses or urgency; otherwise the normal
    workload priority ordering is used.

    The returned text is designed to give the LLM enough grounded evidence
    to answer workload questions without exposing internal thread IDs as
    the primary user-facing reference.
    """
    items = [
        item
        for item in repo.work_items.values()
        if not item.done and item.email_type is EmailType.ACTION
    ]

    normalised = (question or "").lower()

    if any(
        term in normalised
        for term in ("response", "respond", "reply")
    ):
        # Response questions favour inbound messages containing language
        # that indicates the handler is expected to reply or take action.
        response_terms = (
            "please confirm",
            "please advise",
            "please respond",
            "please reply",
            "please review",
            "can you",
            "could you",
            "would you",
            "let us know",
            "let me know",
            "advise next",
            "next steps",
            "confirm",
            "advise",
            "response required",
        )

        def response_score(item: WorkItem) -> tuple[int, int, float]:
            """Score a work item for likely response requirements."""
            thread = repo.threads[item.thread_id]
            text = format_thread(thread).lower()

            latest = max(
                thread.messages,
                key=lambda message: message.date_sent,
            )

            handler_mailbox = os.getenv(
                "HANDLER_MAILBOX",
                "claims@pinnacle-insurance.co.uk",
            ).lower()

            inbound = (
                latest.sent_from.lower() != handler_mailbox
                and any(
                    address.lower() == handler_mailbox
                    for address in latest.sent_to
                )
            )

            return (
                1 if inbound else 0,
                sum(
                    text.count(term)
                    for term in response_terms
                ),
                item.latest_date.timestamp(),
            )

        items.sort(
            key=response_score,
            reverse=True,
        )

    elif any(
        term in normalised
        for term in ("urgent", "urgency", "asap")
    ):
        # Urgency questions favour explicit urgency language in the
        # underlying conversation rather than relying only on AI priority.
        urgency_terms = (
            "urgent",
            "urgently",
            "asap",
            "immediately",
            "immediate",
            "today",
            "deadline",
            "due by",
            "by close of",
            "critical",
            "emergency",
            "without delay",
            "time-sensitive",
            "time sensitive",
        )

        items.sort(
            key=lambda item: (
                sum(
                    format_thread(
                        repo.threads[item.thread_id],
                    ).lower().count(term)
                    for term in urgency_terms
                ),
                item.latest_date.timestamp(),
            ),
            reverse=True,
        )

    else:
        # General workload questions use the application's normal priority
        # and pinning order.
        items = sort_work_items(items)

    items = items[:limit]
    ids = [item.thread_id for item in items]

    lines: list[str] = []

    for item in items:
        thread = repo.threads[item.thread_id]

        latest = max(
            thread.messages,
            key=lambda message: message.date_sent,
        )

        # Keep the evidence concise so a large mailbox does not consume
        # unnecessary context in the LLM request.
        latest_body = " ".join(
            latest.body.split(),
        )[:600]

        handler_mailbox = os.getenv(
            "HANDLER_MAILBOX",
            "claims@pinnacle-insurance.co.uk",
        ).lower()

        inbound_to_handler = (
            any(
                address.lower() == handler_mailbox
                for address in latest.sent_to
            )
            and latest.sent_from.lower() != handler_mailbox
        )

        response_terms = (
            "please confirm",
            "please advise",
            "please respond",
            "please reply",
            "please review",
            "can you",
            "could you",
            "would you",
            "let us know",
            "let me know",
            "advise next",
            "next steps",
            "confirm",
            "advise",
            "response required",
        )

        urgency_terms = (
            "urgent",
            "urgently",
            "asap",
            "immediately",
            "immediate",
            "today",
            "deadline",
            "due by",
            "by close of",
            "critical",
            "emergency",
            "without delay",
            "time-sensitive",
            "time sensitive",
        )

        conversation_text = format_thread(thread).lower()

        likely_response = (
            inbound_to_handler
            and any(
                term in conversation_text
                for term in response_terms
            )
        )

        explicit_urgency = any(
            term in conversation_text
            for term in urgency_terms
        )

        # Use the work item title as the human-readable reference. Internal
        # thread IDs remain available to the application but are not exposed
        # as the main reference for the LLM's response.
        lines.append(
            f"WORK ITEM TITLE: {item.subject}\n"
            f"Work type: {item.email_type.value}\n"
            f"Subject: {item.subject}\n"
            f"Sender: {item.sender}\n"
            f"Latest date: {item.latest_date.isoformat()}\n"
            f"Latest message direction: "
            f"{'Inbound to handler mailbox' if inbound_to_handler else 'Not clearly inbound to handler mailbox'}\n"
            f"Latest message excerpt: {latest_body}\n"
            f"Likely response required from handler: "
            f"{'Yes' if likely_response else 'Not established'}\n"
            f"Explicit urgency language present: "
            f"{'Yes' if explicit_urgency else 'No'}\n"
            f"AI analysis status: {item.analysis_status}\n"
            f"AI priority: "
            f"{item.priority.value if item.priority else 'Not analysed'}\n"
            f"Summary: {item.summary}\n"
            f"Urgency signals: "
            f"{', '.join(item.urgency_signals) or 'Not analysed'}\n"
            f"Importance signals: "
            f"{', '.join(item.importance_signals) or 'Not analysed'}\n"
            f"Actions: "
            f"{', '.join(item.actions) or 'Not analysed'}\n"
        )

    return ids, "\n---\n".join(lines)