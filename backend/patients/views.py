from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Patient, PatientVital, MedicalHistory, MedicalFollowUp, FollowUpMedicine
from .serializers import PatientSerializer, PatientVitalSerializer, MedicalHistorySerializer, MedicalFollowUpSerializer, FollowUpMedicineSerializer
from rest_framework import viewsets

# patient viewset
class PatientViewSet(ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        """
        Always return logged-in user's patient only
        """
        user = self.request.user
        if hasattr(user, "patient"):
            return Patient.objects.filter(
                user=user
            )
        return Patient.objects.none()

    # GET → own patient
    def list(self, request, *args, **kwargs):
        patient = getattr(request.user, "patient", None)

        if not patient:
            return Response([], status=status.HTTP_200_OK)

        serializer = self.get_serializer(patient)
        return Response(serializer.data, status=status.HTTP_200_OK)

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

    # PATCH → update own patient
    def partial_update(self, request, pk=None, *args, **kwargs):
        patient = get_object_or_404(
            Patient,
            pk=pk,
            user=request.user
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

    # CENTRAL SECURITY CHECK
    def _get_patient(self):
        user = self.request.user
        url_patient_id = self.kwargs.get("patient_id")

        if not hasattr(user, "patient"):
            raise PermissionDenied("Only patients can access vitals.")

        if user.patient.id != url_patient_id:
            raise PermissionDenied(
                "You are not allowed to access other patient's vitals."
            )

        return user.patient

    # GET → list vitals
    def get_queryset(self):
        patient = self._get_patient()
        return PatientVital.objects.filter(patient=patient)

    # POST → create new vitals
    def perform_create(self, serializer):
        patient = self._get_patient()
        serializer.save(patient=patient)

# patient vitals viewset
class MedicalHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = MedicalHistorySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch"]

    # default deny (important for medical data)
    queryset = MedicalHistory.objects.none()

    # -------- CENTRAL SECURITY CHECK --------
    def _get_patient(self):
        user = self.request.user
        patient_id = self.kwargs.get("patient_id") or self.kwargs.get("pk")

        if not hasattr(user, "patient"):
            raise PermissionDenied("Only patients can access medical history.")

        if user.patient.id != patient_id:
            raise PermissionDenied(
                "You are not allowed to access other patient's medical history."
            )

        return user.patient

    # -------- LIST --------
    def get_queryset(self):
        patient = self._get_patient()
        return MedicalHistory.objects.filter(patient=patient)

    # -------- CREATE --------
    def perform_create(self, serializer):
        patient = self._get_patient()
        serializer.save(patient=patient)

    # -------- UPDATE --------
    def perform_update(self, serializer):
        patient = self._get_patient()
        instance = serializer.instance

        if instance.patient != patient:
            raise PermissionDenied(
                "You can only update your own medical history."
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

    def _get_followup(self):
        user = self.request.user
        history_id = self.kwargs["history_id"]
        followup_id = self.kwargs["followup_id"]

        if not hasattr(user, "patient"):
            raise PermissionDenied("Only patients allowed.")

        followup = MedicalFollowUp.objects.filter(
            id=followup_id,
            medical_history__id=history_id,
            medical_history__patient=user.patient
        ).first()

        if not followup:
            raise PermissionDenied("Not your follow-up.")

        return followup

    def get_queryset(self):
        followup = self._get_followup()
        return FollowUpMedicine.objects.filter(followup=followup)

    def create(self, request, *args, **kwargs):
        followup = self._get_followup()
        serializer = self.get_serializer(
            data=request.data,
            context={"followup": followup}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        followup = self._get_followup()

        if instance.followup != followup:
            raise PermissionDenied("Not your medicine.")

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

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

    # -------- SECURITY CHECK --------
    def _get_history(self):
        user = self.request.user
        history_id = self.kwargs.get("history_id")

        if not hasattr(user, "patient"):
            raise PermissionDenied("Only patients can access follow-ups.")

        history = MedicalHistory.objects.filter(
            id=history_id,
            patient=user.patient
        ).first()

        if not history:
            raise PermissionDenied(
                "You are not allowed to access this medical history."
            )

        return history

    # -------- LIST --------
    def get_queryset(self):
        history = self._get_history()
        return MedicalFollowUp.objects.filter(medical_history=history)

    # -------- CREATE (FIXED) --------
    def create(self, request, *args, **kwargs):
        history = self._get_history()
        serializer = self.get_serializer(
            data=request.data,
            context={"medical_history": history}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)

    # -------- UPDATE --------
    def perform_update(self, serializer):
        history = self._get_history()
        if serializer.instance.medical_history != history:
            raise PermissionDenied(
                "You can only update your own follow-ups."
            )
        serializer.save()

    # -------- DELETE --------
    def perform_destroy(self, instance):
        history = self._get_history()
        if instance.medical_history != history:
            raise PermissionDenied(
                "You can only delete your own follow-ups."
            )
        instance.delete()
