from rest_framework.permissions import BasePermission
from .models import FamilyMember

class IsFamilyHead(BasePermission):
    message = "Only family head can perform this action."

    def has_permission(self, request, view):
        family_id = view.kwargs.get("family_id") or view.kwargs.get("pk")

        if not family_id:
            return False

        return FamilyMember.objects.filter(
            family_id=family_id,
            patient=request.user.linked_patient,
            is_head=True
        ).exists()
