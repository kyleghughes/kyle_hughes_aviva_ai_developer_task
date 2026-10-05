import os

from .models import Email, EmailType, WorkItem


RULE_VERSION = "work-type-v1"

WORK_TYPE_ORDER = {
    EmailType.ACTION: 0,
    EmailType.INFORMATIONAL: 1,
    EmailType.IRRELEVANT: 2,
}


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
    """Return the searchable text for an email."""
    return f"{email.subject}\n{email.body}".lower()


def classify_thread(
    messages: list[Email],
) -> tuple[EmailType, list[str]]:
    """Classify a thread using deterministic business rules only."""
    text = "\n".join(
        _text(message)
        for message in messages
    )

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

    if action_hits:
        return (
            EmailType.ACTION,
            [
                f"Contains an explicit request or action signal: "
                f"{action_hits[0]}"
            ],
        )

    # A direct message to the configured handler mailbox is treated as
    # workload rather than being silently discarded.
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

    return (
        EmailType.INFORMATIONAL,
        ["Relevant mailbox message with no explicit action signal"],
    )

def sort_work_items(items: list[WorkItem]) -> list[WorkItem]:
    """Sort work using deterministic business workload rules."""
    return sorted(
        items,
        key=lambda item: (
            1 if item.done else 0,
            WORK_TYPE_ORDER[item.email_type],
            -item.latest_date.timestamp(),
            item.thread_id,
        ),
    )


def count_work_items(items: list[WorkItem]) -> dict[str, int]:
    """Return workload counts used by the UI."""
    return {
        "action": sum(
            not item.done and item.email_type is EmailType.ACTION
            for item in items
        ),
        "informational": sum(
            not item.done and item.email_type is EmailType.INFORMATIONAL
            for item in items
        ),
        "irrelevant": sum(
            not item.done and item.email_type is EmailType.IRRELEVANT
            for item in items
        ),
        "done": sum(item.done for item in items),
        "pending": sum(
            not item.done and item.analysis_status != "analyzed"
            for item in items
        ),
    }
