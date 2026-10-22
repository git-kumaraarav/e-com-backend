from rest_framework import permissions, viewsets
from rest_framework.request import Request


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request: Request, view: viewsets.ViewSet) -> bool:  # type: ignore
        return bool(
            request.method in permissions.SAFE_METHODS
            or request.user
            and request.user.is_staff
        )


class IsAdminOrStaff(permissions.BasePermission):
    def has_permission(self, request: Request, view: viewsets.ViewSet) -> bool:  # type: ignore
        return bool(
            request.user
            and (
                request.user.is_authenticated
                and (request.user.is_staff or request.user.is_superuser)
            )
        )
