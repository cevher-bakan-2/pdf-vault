from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        owner = getattr(obj, "owner", None)
        if owner is None and hasattr(obj, "document"):
            owner = getattr(obj.document, "owner", None)
        return owner == request.user


