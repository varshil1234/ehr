from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allows access only to the owner of an object for unsafe methods (PUT, PATCH, DELETE).
    Allows read-only access (GET, HEAD, OPTIONS) to everyone authenticated.
    """

    def has_permission(self, request, view):
        # Allow only authenticated users for all actions
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Read permissions allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions allowed only to the object's owner (assuming `user` field)
        return getattr(obj, "user", None) == request.user
