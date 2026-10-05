import re

from .mailbox import format_thread
from .models import WorkItem
from .prioritisation import sort_work_items
from .repository import MailboxRepository


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
    "what needs doing",
)


def is_workload_question(question: str) -> bool:
    """Detect whether a question asks what work needs attention."""
    normalised = re.sub(
        r"[^a-z0-9' ]+",
        " ",
        question.lower(),
    ).strip()

    if any(
        pattern in normalised
        for pattern in WORKLOAD_PATTERNS
    ):
        return True

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
    """Retrieve the most relevant threads using simple term matching."""
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
        score = sum(text.count(term) for term in terms)

        if score:
            scored.append((score, thread_id))

    scored.sort(key=lambda value: (-value[0], value[1]))

    return [
        thread_id
        for _, thread_id in scored[:limit]
    ]


def workload_evidence(
    repo: MailboxRepository,
    limit: int = 30,
) -> tuple[list[str], str]:
    """Build LLM evidence from the current open workload."""
    items = sort_work_items(
        [
            item
            for item in repo.work_items.values()
            if not item.done
        ],
    )[:limit]

    ids = [item.thread_id for item in items]
    lines: list[str] = []

    for item in items:
        lines.append(
            f"THREAD {item.thread_id}\n"
            f"Work type: {item.email_type.value}\n"
            f"Subject: {item.subject}\n"
            f"Sender: {item.sender}\n"
            f"Latest date: {item.latest_date.isoformat()}\n"
            f"AI analysis status: {item.analysis_status}\n"
            f"Summary: {item.summary}\n"
            f"Urgency signals: "
            f"{', '.join(item.urgency_signals) or 'Not analysed'}\n"
            f"Importance signals: "
            f"{', '.join(item.importance_signals) or 'Not analysed'}\n"
            f"Actions: "
            f"{', '.join(item.actions) or 'Not analysed'}\n"
        )

    return ids, "\n---\n".join(lines)
