from django.db.models import QuerySet
from rest_framework.pagination import CursorPagination
from rest_framework.request import Request


class CursorPaginationExt(CursorPagination):
    page_size = 10
    ordering = "-created_at"

    def get_ordering(
        self, request: Request, queryset: QuerySet, view: object = None
    ) -> tuple[str, ...]:
        ordering = getattr(view, "ordering", None) or self.ordering
        if isinstance(ordering, str):
            return (ordering,)
        return tuple(ordering)
