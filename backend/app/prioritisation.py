import os

from .models import Email, EmailType, Priority, WorkItem


# Version identifier stored with audit information so rule changes can be
# traced independently of AI-generated decisions.
RULE_VERSION = "work-type-v1"


# Lower values appear earlier in the workload ordering.
WORK_TYPE_ORDER = {
    EmailType.ACTION: 0,
    EmailType.INFORMATIONAL: 1,
    EmailType.IRRELEVANT: 2,
}

PRIORITY_ORDER = {
    Priority.HIGH: 0,
    Priority.MEDIUM: 1,
    Priority.LOW: 2,
}


# Terms that strongly suggest an email is noise or does not belong in the
# actionable workload.
IRRELEVANT_TERMS = (
    "unsubscribe",
    "newsletter",
    "marketing",
    "promotional",
    "special offer",
    "meeting invite",
    "delivery notification",
    "out of office",
    "application -",
    "seo rankings",
    "webinar invite",
    "software suite",
    "office lunch",
)


# Terms that explicitly frame an email as informational rather than requiring
# work from the handler.
INFORMATIONAL_TERMS = (
    "for your information",
    "for information",
    "for your records",
    "fyi",
    "no action required",
    "no action needed",
    "just to let you know",
    "please note",
)


# Terms that indicate the recipient is being asked to do something.
ACTION_TERMS = (
    "please review",
    "please confirm",
    "please provide",
    "please send",
    "please arrange",
    "please approve",
    "please authorise",
    "please authorize",
    "please respond",
    "please advise",
    "please action",
    "action required",
    "action is required",
    "we need you to",
    "could you",
    "can you",
    "would you",
    "requesting",
    "requires your",
    "need your",
    "awaiting your",
    "open a claim",
    "register a claim",
    "arrange a hire",
)


def _text(email: Email) -> str:
    """Return the subject and body as lowercase searchable text."""
    return f"{email.subject}\n{email.body}".lower()


def classify_thread(
    messages: list[Email],
) -> tuple[EmailType, list[str]]:
    """Classify a thread using deterministic business rules.

    Classification deliberately does not use the LLM. The rules provide
    predictable workflow routing, while AI analysis is used separately
    for decision support such as priority and workload interpretation.
    """
    text = "\n".join(
        _text(message)
        for message in messages
    )

    # Noise is classified as irrelevant unless the same thread contains
    # an explicit action request, which takes precedence.
    irrelevant_hits = [
        term
        for term in IRRELEVANT_TERMS
        if term in text
    ]

    if irrelevant_hits and not any(
        term in text
        for term in ACTION_TERMS
    ):
        return (
            EmailType.IRRELEVANT,
            [
                f"Contains {', '.join(irrelevant_hits[:2])} language",
            ],
        )

    # Identify explicit informational and action signals before deciding
    # between the remaining workflow categories.
    informational_hits = [
        term
        for term in INFORMATIONAL_TERMS
        if term in text
    ]

    action_hits = [
        term
        for term in ACTION_TERMS
        if term in text
    ]

    # An explicit "no action" statement overrides other informational
    # wording because it directly describes the required workflow.
    if any(
        term in text
        for term in ("no action required", "no action needed")
    ):
        return (
            EmailType.INFORMATIONAL,
            ["Explicitly states that no action is required"],
        )

    if informational_hits and not action_hits:
        return (
            EmailType.INFORMATIONAL,
            ["Explicitly framed as informational or requiring no action"],
        )

    # Any explicit action signal makes the thread actionable.
    if action_hits:
        return (
            EmailType.ACTION,
            [
                f"Contains an explicit request or action signal: "
                f"{action_hits[0]}"
            ],
        )

    # A direct message to the configured handler mailbox is treated as
    # workload rather than being silently discarded when no stronger
    # informational or noise signal was found.
    latest = max(
        messages,
        key=lambda message: message.date_sent,
    )

    handler_mailbox = os.getenv(
        "HANDLER_MAILBOX",
        "claims@pinnacle-insurance.co.uk",
    ).lower()

    if any(
        address.lower() == handler_mailbox
        for address in latest.sent_to
    ):
        return (
            EmailType.ACTION,
            [
                "Sent directly to the handler mailbox without "
                "an informational/noise signal",
            ],
        )

    # If the thread contains no explicit action, informational, or noise
    # signal, keep it visible as informational rather than treating it
    # as irrelevant.
    return (
        EmailType.INFORMATIONAL,
        ["Relevant mailbox message with no explicit action signal"],
    )


def sort_work_items(items: list[WorkItem]) -> list[WorkItem]:
    """Sort workload items into the order used by the UI.

    Unactioned work is shown before actioned work. Within the active
    workload, pinned items come first, followed by AI/manual priority
    and then the most recently updated threads.
    """
    return sorted(
        items,
        key=lambda item: (
            1 if item.done else 0,
            0 if item.pinned else 1,
            PRIORITY_ORDER.get(item.priority, 3),
            -item.latest_date.timestamp(),
            item.thread_id,
        ),
    )


def count_work_items(items: list[WorkItem]) -> dict[str, int]:
    """Return workload counts used by the UI.

    Counts are derived from the current work-item state so they reflect
    category, workflow status, and whether AI analysis has been completed.
    """
    return {
        "action": sum(
            not item.done
            and item.email_type is EmailType.ACTION
            for item in items
        ),
        "archive": sum(
            not item.done
            and item.email_type is not EmailType.ACTION
            for item in items
        ),
        "informational": sum(
            not item.done
            and item.email_type is EmailType.INFORMATIONAL
            for item in items
        ),
        "irrelevant": sum(
            not item.done
            and item.email_type is EmailType.IRRELEVANT
            for item in items
        ),
        "done": sum(
            item.done
            for item in items
        ),
        "in_progress": sum(
            item.in_progress
            and not item.done
            and item.email_type is EmailType.ACTION
            for item in items
        ),
        "pending": sum(
            not item.done
            and item.email_type is EmailType.ACTION
            and item.analysis_status != "analyzed"
            for item in items
        ),
    }