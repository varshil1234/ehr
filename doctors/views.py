from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .serializers import DoctorSerializer, Doctor, AccessRequestCreateSerializer, AccessRequestVerifySerializer, AccessRequest, EncounterSerializer, Encounter, ClinicalNoteSerializer, ClinicalNote
from utils.permissions import IsOwnerOrReadOnly
from families.models import FamilyMember

# Create your views here.
class DoctorViewSet(viewsets.ModelViewSet):
    serializer_class = DoctorSerializer
    queryset = Doctor.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['specialty', 'hospital']
    ordering_fields = ['id', 'name', 'hospital']
    search_fields = ['id', 'name', 'hospital', 'contact_number']
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


class AccessRequestViewSet(viewsets.ModelViewSet):
    queryset = AccessRequest.objects.all()
    serializer_class = AccessRequestCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Doctors can see only their own requests; patients can see requests about them
        if hasattr(user, 'doctor_profile'):
            return AccessRequest.objects.filter(doctor=user.doctor_profile)
        elif hasattr(user, 'patient_profile'):
            return AccessRequest.objects.filter(patient=user.patient_profile)
        return AccessRequest.objects.none()

    def perform_create(self, serializer):
        # Attach logged-in doctor automatically
        user = self.request.user
        if user.role != 'doctor':
            return Response({"detail": "Only doctors can create access requests."},
                            status=status.HTTP_403_FORBIDDEN)
        serializer.save(doctor=user.linked_doctor)

    def create(self, request, *args, **kwargs):
        # Override create to validate and send OTP
        user = request.user
        if user.role != 'doctor':
            return Response({"detail": "Only doctors can create access requests."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        access_request = serializer.save(doctor=user.linked_doctor)

        headers = self.get_success_headers(serializer.data)
        return Response(
            AccessRequestCreateSerializer(access_request).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        return Response({"detail": "Update not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"], url_path="verify-otp")
    def verify_otp(self, request, pk=None):
        # Verify OTP sent to patient email and approve access
        access_request = self.get_object()
        serializer = AccessRequestVerifySerializer(
            data=request.data, context={"access_request": access_request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Access approved successfully."}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=["post"], url_path="resend-otp")
    def resend_otp(self, request, pk=None):
        access_request = self.get_object()
        user = request.user

        # Only the doctor who created this request can resend the OTP
        if not hasattr(user, "doctor_profile") or access_request.doctor != user.doctor_profile:
            return Response(
                {"detail": "Only the doctor who created this request can resend OTP."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Prevent spamming - allow resend only after 1 minute
        if (
            access_request.otp_expires_at
            and access_request.otp_expires_at > timezone.now()
            and access_request.otp_expires_at - timedelta(minutes=9) > timezone.now()
        ):
            return Response(
                {"detail": "OTP was recently sent. Please wait before resending."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Generate a new OTP
        otp = access_request.generate_otp()

        # TODO: Send the OTP via email
        
        return Response(
            {"detail": "A new OTP has been sent to the patient's registered email."},
            status=status.HTTP_200_OK
        )


class EncounterViewSet(viewsets.ModelViewSet):
    serializer_class = EncounterSerializer
    queryset = Encounter.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['patient']
    ordering_fields = ['id', 'patient__first_name', 'patient__last_name']
    search_fields = ['id']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Normal users see only their own record.
        Doctors/labs can see access request approved patient's records.
        Family Heads can see their family members' records.
        """
        user = self.request.user
        if user.role == 'patient':
            # Family head can see vitals for patients they have approved access to
            approved_patient_ids = FamilyMember.objects.filter(
                family__head_of_family=user.linked_patient, is_verified=True
            ).values_list('patient_id', flat=True)

            patient_id = user.linked_patient.id
            approved_patient_ids = list(approved_patient_ids) + [patient_id]

            return self.queryset.filter(patient_id__in=approved_patient_ids)
        elif user.role == 'doctor':
            doctor = user.linked_doctor.id

            # Doctor can see encounters for patients they have approved access to
            approved_patient_ids = AccessRequest.objects.filter(
                doctor=doctor, is_approved=True
            ).values_list('patient_id', flat=True)

            return self.queryset.filter(patient_id__in=approved_patient_ids)
        else:
            return Encounter.objects.none()

    def perform_create(self, serializer):
        # Associate the vitals with the patient's record if the user is a patient
        user = self.request.user
        if user.role != 'doctor':
            raise PermissionDenied("Only doctors are allowed to create encounter.")
        
        # Ensure 'patient' is included in request
        patient = serializer.validated_data.get('patient')
        if not patient:
            raise PermissionDenied("Patient information is required.")
        
        doctor = user.doctor_profile
        # Check if doctor has approved access for the patient
        has_access = AccessRequest.objects.filter(
            doctor=doctor,
            patient=patient,
            is_approved=True
        ).exists()

        if not has_access:
            raise PermissionDenied("You do not have approved access to this patient.")

        # Save with doctor automatically assigned
        serializer.save(doctor=doctor)

    def perform_update(self, serializer):
        user = self.request.user

        # Only doctors can update encounters
        if user.role != 'doctor' or not hasattr(user, 'doctor_profile'):
            raise PermissionDenied("Only doctors are allowed to update encounter.")

        doctor = user.doctor_profile
        encounter = self.get_object()

        # Ensure doctor is the owner of the encounter
        if encounter.doctor != doctor:
            raise PermissionDenied("You can only update encounters you have created.")

        # Remove 'patient' and 'doctor' from update data if present
        serializer.validated_data.pop('patient', None)
        serializer.validated_data.pop('doctor', None)

        # Ensure doctor still has approved access to this encounter’s patient
        has_access = AccessRequest.objects.filter(
            doctor=doctor,
            patient=encounter.patient,
            is_approved=True
        ).exists()

        if not has_access:
            raise PermissionDenied("You do not have approved access to this patient.")

        # Save without reassigning doctor/patient
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        # Only doctors can delete
        if user.role != 'doctor' or not hasattr(user, 'doctor_profile'):
            raise PermissionDenied("Only doctors are allowed to delete encounters.")

        doctor = user.doctor_profile

        # Only the doctor who created the encounter can delete it
        if instance.doctor != doctor:
            raise PermissionDenied("You can only delete encounters you have created.")

        # Doctor must still have approved access to the patient
        has_access = AccessRequest.objects.filter(
            doctor=doctor,
            patient=instance.patient,
            is_approved=True
        ).exists()

        if not has_access:
            raise PermissionDenied("You do not have approved access to this patient.")

        # If all checks pass, delete
        instance.delete()


class ClinicalNoteViewSet(viewsets.ModelViewSet):
    serializer_class = ClinicalNoteSerializer
    queryset = ClinicalNote.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['encounter__patient']
    ordering_fields = ['id', 'encounter__patient__first_name', 'encounter__patient__last_name']
    search_fields = ['id']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Normal users see only their own record.
        Doctors/labs can see access request approved patient's records.
        Family Heads can see their family members' records.
        """
        user = self.request.user
        if user.role == 'patient':
            # Family head can see vitals for patients they have approved access to
            approved_patient_ids = FamilyMember.objects.filter(
                family__head_of_family=user.linked_patient, is_verified=True
            ).values_list('patient_id', flat=True)

            patient_id = user.linked_patient.id
            approved_patient_ids = list(approved_patient_ids) + [patient_id]

            return self.queryset.filter(encounter__patient_id__in=approved_patient_ids)
        elif user.role == 'doctor':
            doctor = user.linked_doctor.id

            # Doctor can see encounters for patients they have approved access to
            approved_patient_ids = AccessRequest.objects.filter(
                doctor=doctor, is_approved=True
            ).values_list('patient_id', flat=True)

            return self.queryset.filter(encounter__patient_id__in=approved_patient_ids)
        else:
            return Encounter.objects.none()

    def perform_create(self, serializer):
        user = self.request.user

        # Only doctors can create clinical notes
        if user.role != 'doctor' or not hasattr(user, 'doctor_profile'):
            raise PermissionDenied("Only doctors are allowed to create clinical notes.")

        doctor = user.doctor_profile

        # Get encounter from request data
        encounter = serializer.validated_data.get('encounter')
        if not encounter:
            raise PermissionDenied("Encounter information is required to create a clinical note.")

        # Ensure doctor created that encounter
        if encounter.doctor != doctor:
            raise PermissionDenied("You can only add clinical notes to encounters you created.")

        # Ensure the encounter’s access is still valid
        has_access = AccessRequest.objects.filter(
            doctor=doctor,
            patient=encounter.patient,
            is_approved=True
        ).exists()

        if not has_access:
            raise PermissionDenied("You do not have approved access to this patient.")

        # Save note
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user

        # Only doctors can update clinical notes
        if user.role != 'doctor' or not hasattr(user, 'doctor_profile'):
            raise PermissionDenied("Only doctors are allowed to update clinical notes.")

        doctor = user.doctor_profile
        note = self.get_object()
        encounter = note.encounter  # Linked encounter

        # Ensure the doctor created the encounter for this clinical note
        if encounter.doctor != doctor:
            raise PermissionDenied("You can only update clinical notes for encounters you created.")

        # Ensure the doctor still has approved access to the patient
        has_access = AccessRequest.objects.filter(
            doctor=doctor,
            patient=encounter.patient,
            is_approved=True
        ).exists()

        if not has_access:
            raise PermissionDenied("You do not have approved access to this patient.")

        # Prevent updates to immutable fields
        immutable_fields = ['encounter']
        for field in immutable_fields:
            serializer.validated_data.pop(field, None)

        # Save updated note
        serializer.save()        
        
    def perform_destroy(self, instance):
        user = self.request.user

        # Only doctors can delete
        if user.role != 'doctor' or not hasattr(user, 'doctor_profile'):
            raise PermissionDenied("Only doctors are allowed to delete clinical notes.")

        doctor = user.doctor_profile

        # Only the doctor who created the encounter can delete it
        if instance.encounter.doctor != doctor:
            raise PermissionDenied("You can only delete clinical notes you have created.")

        # Doctor must still have approved access to the patient
        has_access = AccessRequest.objects.filter(
            doctor=doctor,
            patient=instance.encounter.patient,
            is_approved=True
        ).exists()

        if not has_access:
            raise PermissionDenied("You do not have approved access to this patient.")

        # If all checks pass, delete
        instance.delete()
