from dataclasses import dataclass

from .models import WorkItem
from .prioritisation import count_work_items, sort_work_items


@dataclass(frozen=True)
class WorkItemPage:
    """Paginated workload results and summary counts."""

    items: list[WorkItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    counts: dict[str, int]

    def as_dict(self) -> dict:
        """Return the page in API-friendly dictionary form."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "counts": self.counts,
        }


def _matches(
    item: WorkItem,
    query: str,
) -> bool:
    """Check whether a workload item matches a search query."""
    value = query.strip().lower()

    if not value:
        return True

    fields = (
        item.thread_id,
        item.subject,
        item.sender,
        item.topic or "",
        item.summary,
    )

    return any(value in field.lower() for field in fields)


def paginate_work_items(
    items: list[WorkItem],
    *,
    page: int = 1,
    page_size: int = 10,
    query: str = "",
    filter_name: str = "action",
) -> WorkItemPage:
    """Filter, sort and paginate workload items."""
    if page < 1:
        raise ValueError("page must be at least 1")

    if page_size < 1 or page_size > 100:
        raise ValueError("page_size must be between 1 and 100")

    valid_filters = {
        "action",
        "in_progress",
        "archive",
        "done",
    }

    if filter_name not in valid_filters:
        raise ValueError("invalid filter")

    filtered = [
        item
        for item in items
        if _matches(item, query)
    ]

    if filter_name == "action":
        filtered = [item for item in filtered if not item.done and not item.in_progress and item.email_type.value == "action"]
    elif filter_name == "in_progress":
        filtered = [item for item in filtered if not item.done and item.in_progress and item.email_type.value == "action"]
    elif filter_name == "archive":
        filtered = [item for item in filtered if not item.done and item.email_type.value in {"informational", "irrelevant"}]
    else:
        filtered = [item for item in filtered if item.done]

    ordered = sort_work_items(filtered)
    total = len(ordered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    safe_page = min(page, total_pages)
    start = (safe_page - 1) * page_size

    return WorkItemPage(
        items=ordered[start : start + page_size],
        total=total,
        page=safe_page,
        page_size=page_size,
        total_pages=total_pages,
        counts=count_work_items(items),
    )
