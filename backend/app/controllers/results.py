"""Transport-agnostic result carriers returned by controllers.

A controller returns *domain results*, not HTTP envelopes — the view layer is
what wraps them in ``APIResponse`` / ``PaginatedResponse`` (see the layering
table in ``backend/README.md``). :class:`Page` is the shape a paginated read
returns: the slice of items plus the total matching count. Keeping page/per_page
out of it is deliberate — those are request inputs the view already holds, so
the controller stays free of pagination presentation concerns.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Page[T]:
    """One page of results plus the total count of matching rows.

    ``total`` is the count *across all pages* (what drives ``PaginationMeta``),
    not ``len(items)`` — the two differ on every page but the last.
    """

    items: list[T]
    total: int
