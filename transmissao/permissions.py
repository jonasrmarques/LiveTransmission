"""Permissions for the transmissao domain."""

from rest_framework.permissions import BasePermission

from transmissao.room_access import ensure_room_access, user_is_owner


class IsRoomParticipant(BasePermission):
    """User must be an active participant or owner of the room."""

    def has_object_permission(self, request, view, obj) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            ensure_room_access(obj, request.user)
        except Exception:
            return False
        return True


class IsRoomOwner(BasePermission):
    """User must be the room owner."""

    def has_object_permission(self, request, view, obj) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        return user_is_owner(obj, request.user)
