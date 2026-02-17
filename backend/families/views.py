from urllib import request
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch
from users.models import OTP
from .models import Family, FamilyMember
from rest_framework import status
from .serializers import (FamilySerializer,AddFamilyMemberSerializer,SendFamilyMemberOTPSerializer,VerifyFamilyMemberOTPSerializer)

# Family ViewSet
class FamilyViewSet(viewsets.ModelViewSet):

    serializer_class = FamilySerializer
    permission_classes = [IsAuthenticated]

    # -------- LIST / RETRIEVE --------
    def get_queryset(self):

        user = self.request.user

        if not hasattr(user, "patient"):
            return Family.objects.none()

        return Family.objects.select_related(
            "head_of_family",
            "head_of_family__user"
        ).prefetch_related(
            Prefetch("members")
        ).filter(
            head_of_family=user.patient
        )

    # -------- CREATE --------
    def perform_create(self, serializer):

        user = self.request.user

        if not hasattr(user, "patient"):
            raise PermissionDenied(
                "Only patients can create a family."
            )

        serializer.save(
            head_of_family=user.patient
        )

    # -------- UPDATE --------
    def perform_update(self, serializer):

        family = self.get_object()
        user = self.request.user

        if family.head_of_family != user.patient:
            raise PermissionDenied(
                "You can only update your own family."
            )

        serializer.save()

    # -------- DELETE --------
    def perform_destroy(self, instance):

        user = self.request.user

        if instance.head_of_family != user.patient:
            raise PermissionDenied(
                "You can only delete your own family."
            )

        instance.delete()

# Family Member OTP ViewSet
class FamilyMemberOTPViewSet(viewsets.ViewSet):

    permission_classes = [IsAuthenticated]

    # -------- SEND OTP --------
    @action(detail=False, methods=["post"])
    def send_otp(self, request):

        serializer = SendFamilyMemberOTPSerializer(
            data=request.data,
            context={"request": request}
        )

        serializer.is_valid(raise_exception=True)

        return Response(serializer.save())

    # -------- VERIFY OTP --------
    @action(detail=False, methods=["post"])
    def verify_otp(self, request):

        serializer = VerifyFamilyMemberOTPSerializer(
            data=request.data,
            context={"request": request}
        )

        serializer.is_valid(raise_exception=True)

        return Response(serializer.save())

# Family Member ViewSet
class FamilyMemberViewSet(viewsets.ModelViewSet):

    serializer_class = AddFamilyMemberSerializer
    permission_classes = [IsAuthenticated]

    # -------- LIST MEMBERS --------
    def get_queryset(self):

        user = self.request.user

        if not hasattr(user, "patient"):
            return FamilyMember.objects.none()

        return FamilyMember.objects.select_related(
            "family",
            "patient",
            "patient__user"
        ).filter(
            family__head_of_family=user.patient
        )

    # -------- ADD MEMBER --------
    def perform_create(self, serializer):

        user = self.request.user

        if not hasattr(user, "patient"):
            raise PermissionDenied(
                "Only patients can add family members."
            )

        serializer.save()

    # -------- REMOVE MEMBER --------
    def destroy(self, request, *args, **kwargs):
    
        instance = self.get_object()

        user = request.user

        if not hasattr(user, "patient"):
            raise PermissionDenied(
                "Only patients can remove family members."
        )

        if instance.family.head_of_family != user.patient:
            raise PermissionDenied(
                "Only family head can remove members."
        )

        # IMPORTANT: Reset OTP verification
        OTP.objects.filter(
            user=instance.patient.user,
            purpose="family_member_add"
        ).update(is_used=False)

        # Delete member
        instance.delete()

        return Response(
            {"detail": "Patient removed from family successfully."},
            status=status.HTTP_200_OK  
        )
      