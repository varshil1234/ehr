from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from lab_reports.models import LabReport
from lab_reports.serializers import LabReportSerializer
from patients.models import Patient
from families.models import FamilyMember

class LabReportViewSet(viewsets.ModelViewSet):
    
    serializer_class = LabReportSerializer
    permission_classes = [IsAuthenticated]

    # GET PATIENT FROM URL AND VALIDATE ACCESS
    def get_patient(self):

        patient_id = self.kwargs.get("patient_id")

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            raise PermissionDenied("Patient not found.")

        if not hasattr(self.request.user, "patient"):
            raise PermissionDenied("User is not a patient.")

        logged_patient = self.request.user.patient

        # CASE 1: Own access
        if logged_patient.id == patient.id:
            return patient

        # CASE 2: Family head access (verified members only)
        is_family_head = FamilyMember.objects.filter(
            patient=patient,
            family__head_of_family=logged_patient,
            is_verified=True
        ).exists()

        if is_family_head:
            return patient

        # Otherwise → No access
        raise PermissionDenied(
            "You do not have permission to access this patient's reports."
        )

    # LIST & RETRIEVE
    def get_queryset(self):

        patient = self.get_patient()

        return LabReport.objects.select_related(
            "patient"
        ).filter(
            patient=patient
        )

    # CREATE REPORT
    def perform_create(self, serializer):

        patient = self.get_patient()

        serializer.save(
            patient=patient
        )

    # UPDATE REPORT
    def perform_update(self, serializer):

        patient = self.get_patient()

        report = self.get_object()

        if report.patient != patient:
            raise PermissionDenied(
                "You can update only authorized patient reports."
            )

        serializer.save()

    # DELETE REPORT
    def destroy(self, request, *args, **kwargs):

        patient = self.get_patient()

        instance = self.get_object()

        if instance.patient != patient:
            raise PermissionDenied(
                "You can delete only authorized patient reports."
            )

        instance.delete()

        return Response(
            {"detail": "Report deleted successfully."},
            status=status.HTTP_200_OK
        )
