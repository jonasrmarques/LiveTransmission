"""Permissions for the usuarios domain."""

from rest_framework.permissions import BasePermission


class IsAuthenticatedUser(BasePermission):
    """Allows access only to authenticated users."""

    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)


class IsSelf(BasePermission):
    """Object-level: user may only access their own record."""

    def has_object_permission(self, request, view, obj) -> bool:
        return bool(request.user and request.user.is_authenticated and obj == request.user)
