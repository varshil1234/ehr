from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Family, FamilyMember
from .serializers import FamilySerializer, FamilyMemberSerializer


class FamilyViewSet(viewsets.ModelViewSet):
    queryset = Family.objects.all()
    serializer_class = FamilySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'patient':
            patient_id = user.linked_patient.id
            return Family.objects.filter(head_of_family__id=patient_id)
        else:
            return Family.objects.none()
        
    def perform_create(self, serializer):
        user = self.request.user
        if user.role != 'patient':
            raise PermissionDenied("Only patients are allowed to create Family.")
    
        serializer.save(head_of_family=user.linked_patient)

    def perform_update(self, serializer):
        user = self.request.user
        family = self.get_object()  # current vital being updated

        # Patient can only update their own vitals
        if user.role == "patient":
            if family.head_of_family == user.linked_patient:
                serializer.validated_data.pop('head_of_family', None)
                serializer.save()
                return
            else:
                raise PermissionDenied("You can only update your own family.")

        # All other roles are denied
        raise PermissionDenied("You are not allowed to update family.")


class FamilyMemberViewSet(viewsets.ModelViewSet):
    queryset = FamilyMember.objects.all()
    serializer_class = FamilyMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Allow only the head of a family to view members.
        user = self.request.user
        if user.role == 'patient':
            patient_id = user.linked_patient.id
            return FamilyMember.objects.filter(family__head_of_family__id=patient_id)
        else:
            return FamilyMember.objects.none()
        
    def perform_create(self, serializer):
        # Allow only the head of a family to add members.
        user = self.request.user
        family = serializer.validated_data.get('family')

        if user.role != 'patient':
            raise PermissionDenied("Only patients are allowed to add Family members.")
    
        # Only head of the family can add members
        if family.head_of_family != user.linked_patient:
            raise PermissionDenied("Only the head of this family can add members.")

        serializer.save()

    def perform_destroy(self, instance):
        # Allow only the head of a family to delete members.
        user = self.request.user

        if user.role != 'patient':
            raise PermissionDenied("Only patients are allowed to delete Family members.")

        # Only head of the family can delete members
        if instance.family.head_of_family != user.linked_patient:
            raise PermissionDenied("Only the head of this family can remove members.")

        instance.delete()
