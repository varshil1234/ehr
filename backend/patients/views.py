from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Patient, PatientVital, MedicalHistory, MedicalFollowUp, FollowUpMedicine
from .serializers import PatientSerializer, PatientVitalSerializer, MedicalHistorySerializer, MedicalFollowUpSerializer, FollowUpMedicineSerializer
from rest_framework import viewsets
from families.models import FamilyMember

def get_accessible_patient_ids(user):
    """
    Access allowed to:
    - Own patient
    - OTP verified family members (ONLY if user is family head)
    """
    if not hasattr(user, "patient"):
        return []

    own_id = user.patient.id

    family_member_ids = FamilyMember.objects.filter(
        family__head_of_family=user.patient,
        is_verified=True
    ).values_list("patient_id", flat=True)

    return list(set([own_id] + list(family_member_ids)))

# patient viewset
class PatientViewSet(ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        allowed_ids = get_accessible_patient_ids(self.request.user)
        return Patient.objects.filter(id__in=allowed_ids)

    # GET → own + verified family members
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # POST → create patient (only once)
    def create(self, request, *args, **kwargs):
        if hasattr(request.user, "patient"):
            raise PermissionDenied("Patient profile already exists")

        serializer = self.get_serializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()

        return Response(
            self.get_serializer(patient).data,
            status=status.HTTP_201_CREATED
        )

    # PATCH → update own OR verified family members profile
    def partial_update(self, request, pk=None, *args, **kwargs):
        allowed_ids = get_accessible_patient_ids(request.user)
        
        # Check if the patient being updated is in allowed_ids
        patient = get_object_or_404(
            Patient,
            pk=pk,
            id__in=allowed_ids
        )

        serializer = self.get_serializer(
            patient,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "status": "success",
                "detail": "Patient updated successfully"
            },
            status=status.HTTP_200_OK
        )

#patinet vitals viewset
class PatientVitalsViewSet(ModelViewSet):
    serializer_class = PatientVitalSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post"]

    # CENTRAL ACCESS LOGIC
    def _get_patient(self):
        user = self.request.user
        url_patient_id = self.kwargs.get("patient_id")
        allowed_ids = get_accessible_patient_ids(user)

        if int(url_patient_id) in allowed_ids:
            return Patient.objects.get(id=url_patient_id)

        raise PermissionDenied(
            "You are not allowed to access other patient's vitals."
        )

    # GET → list vitals (self + verified family members)
    def get_queryset(self):
        patient = self._get_patient()
        return PatientVital.objects.filter(patient=patient)

    # POST → create vitals (Self + verified family members)
    def perform_create(self, serializer):
        patient = self._get_patient() # This checks permission
        serializer.save(patient=patient)

# patient medical history viewset
class MedicalHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = MedicalHistorySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch"]

    queryset = MedicalHistory.objects.none()

    # -------- CENTRAL ACCESS CHECK --------
    def _get_patient(self):
        user = self.request.user
        patient_id = self.kwargs.get("patient_id") or self.kwargs.get("pk")
        allowed_ids = get_accessible_patient_ids(user)

        if int(patient_id) in allowed_ids:
            return Patient.objects.get(id=patient_id)

        raise PermissionDenied(
            "You are not allowed to access other patient's medical history."
        )

    # -------- LIST (GET) --------
    def get_queryset(self):
        patient = self._get_patient()
        return MedicalHistory.objects.filter(patient=patient)

    # -------- CREATE (POST) --------
    def perform_create(self, serializer):
        patient = self._get_patient() # Allows family head for verified members
        serializer.save(patient=patient)

    # -------- UPDATE (PATCH) --------
    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance
        allowed_ids = get_accessible_patient_ids(user)

        if instance.patient.id not in allowed_ids:
            raise PermissionDenied(
                "You can only update allowed patient's medical history."
            )

        serializer.save()

    # -------- DELETE (DISABLED) --------
    def perform_destroy(self, instance):
        raise PermissionDenied(
            "Medical history deletion is not allowed."
        )
        
# patient medical followups viewset
class FollowUpMedicineViewSet(viewsets.ModelViewSet):
    serializer_class = FollowUpMedicineSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    # -------- CENTRAL FOLLOWUP ACCESS --------
    def _get_followup(self):
        user = self.request.user
        history_id = self.kwargs["history_id"]
        followup_id = self.kwargs["followup_id"]
        allowed_ids = get_accessible_patient_ids(user)

        # Updated to check verified family members access
        followup = MedicalFollowUp.objects.filter(
            id=followup_id,
            medical_history__id=history_id,
            medical_history__patient_id__in=allowed_ids
        ).first()

        if followup:
            return followup

        raise PermissionDenied("Not your follow-up or no permission.")

    # -------- LIST (GET) --------
    def get_queryset(self):
        followup = self._get_followup()
        return FollowUpMedicine.objects.filter(followup=followup)

    # -------- CREATE (POST) --------
    def create(self, request, *args, **kwargs):
        followup = self._get_followup() # Logic allows verified family access
        
        serializer = self.get_serializer(
            data=request.data,
            context={"followup": followup}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)

    # -------- UPDATE (PATCH) --------
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        followup = self._get_followup()

        if instance.followup != followup:
            raise PermissionDenied("Not your medicine.")

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    # -------- DELETE --------
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        followup = self._get_followup()

        if instance.followup != followup:
            raise PermissionDenied("Not your medicine.")

        instance.delete()
        return Response({"detail": "Medicine deleted"})

class MedicalFollowUpViewSet(viewsets.ModelViewSet):
    serializer_class = MedicalFollowUpSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    queryset = MedicalFollowUp.objects.none()

    # -------- CENTRAL SECURITY CHECK --------
    def _get_history(self):
        user = self.request.user
        history_id = self.kwargs.get("history_id")
        allowed_ids = get_accessible_patient_ids(user)

        history = MedicalHistory.objects.filter(
            id=history_id,
            patient_id__in=allowed_ids
        ).first()

        if history:
            return history

        raise PermissionDenied(
            "You are not allowed to access this medical history."
        )

    # -------- LIST (GET) --------
    def get_queryset(self):
        history = self._get_history()
        return MedicalFollowUp.objects.filter(
            medical_history=history
        )

    # -------- CREATE (POST) --------
    def create(self, request, *args, **kwargs):
        history = self._get_history()

        serializer = self.get_serializer(
            data=request.data,
            context={"medical_history": history}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)

    # -------- UPDATE (PATCH) --------
    def perform_update(self, serializer):
        history = self._get_history()

        if serializer.instance.medical_history != history:
            raise PermissionDenied(
                "You can only update allowed follow-ups."
            )

        serializer.save()

    # -------- DELETE --------
    def perform_destroy(self, instance):
        history = self._get_history()

        if instance.medical_history != history:
            raise PermissionDenied(
                "You can only delete allowed follow-ups."
            )

        instance.delete()
