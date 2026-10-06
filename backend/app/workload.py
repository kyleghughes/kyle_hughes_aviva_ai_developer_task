from dataclasses import dataclass

from .models import WorkItem
from .prioritisation import count_work_items, sort_work_items


@dataclass(frozen=True)
class WorkItemPage:
    """Paginated workload results together with summary counts."""

    items: list[WorkItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    counts: dict[str, int]

    def as_dict(self) -> dict:
        """Return the page in a dictionary suitable for API responses."""
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
    """Return whether a workload item matches the supplied search text.

    Search is intentionally simple and deterministic. It checks the
    thread ID, subject, sender, AI topic, and summary.
    """
    value = query.strip().lower()

    # An empty search should not exclude any items.
    if not value:
        return True

    searchable_fields = (
        item.thread_id,
        item.subject,
        item.sender,
        item.topic or "",
        item.summary,
    )

    return any(
        value in field.lower()
        for field in searchable_fields
    )


def paginate_work_items(
    items: list[WorkItem],
    *,
    page: int = 1,
    page_size: int = 10,
    query: str = "",
    filter_name: str = "action",
) -> WorkItemPage:
    """Filter, sort, and paginate the workload.

    Supported views are:

    - ``action`` — actionable items not yet started.
    - ``in_progress`` — actionable items currently being worked on.
    - ``archive`` — informational and irrelevant items.
    - ``done`` — actioned items.

    The returned page is safely clamped to the final available page when
    the requested page number is beyond the end of the result set.
    """
    if page < 1:
        raise ValueError("page must be at least 1")

    if page_size < 1 or page_size > 100:
        raise ValueError(
            "page_size must be between 1 and 100",
        )

    valid_filters = {
        "action",
        "in_progress",
        "archive",
        "done",
    }

    if filter_name not in valid_filters:
        raise ValueError("invalid filter")

    # Apply the free-text search before applying the workflow filter.
    filtered = [
        item
        for item in items
        if _matches(item, query)
    ]

    if filter_name == "action":
        # Only actionable work that has not yet been started belongs here.
        filtered = [
            item
            for item in filtered
            if (
                not item.done
                and not item.in_progress
                and item.email_type.value == "action"
            )
        ]

    elif filter_name == "in_progress":
        # Work that has explicitly been started but is not yet actioned.
        filtered = [
            item
            for item in filtered
            if (
                not item.done
                and item.in_progress
                and item.email_type.value == "action"
            )
        ]

    elif filter_name == "archive":
        # Informational and irrelevant emails are read-only archive items.
        filtered = [
            item
            for item in filtered
            if (
                not item.done
                and item.email_type.value in {
                    "informational",
                    "irrelevant",
                }
            )
        ]

    else:
        # The remaining filter is the Actioned view.
        filtered = [
            item
            for item in filtered
            if item.done
        ]

    # Apply the shared workload ordering after filtering so pinned items,
    # priority, and recency are handled consistently across views.
    ordered = sort_work_items(filtered)

    total = len(ordered)

    # Always expose at least one page, including when there are no results.
    total_pages = max(
        1,
        (total + page_size - 1) // page_size,
    )

    # Prevent an out-of-range page from producing an empty result when
    # the caller has requested a page beyond the final page.
    safe_page = min(
        page,
        total_pages,
    )

    start = (safe_page - 1) * page_size

    return WorkItemPage(
        items=ordered[start : start + page_size],
        total=total,
        page=safe_page,
        page_size=page_size,
        total_pages=total_pages,
        counts=count_work_items(items),
    )