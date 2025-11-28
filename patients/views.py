from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import SearchFilter, OrderingFilter
from .serializers import PatientSerializer, Patient, VitalsSerializer, Vital, MedicalHistorySerializer, MedicalHistory
from utils.permissions import IsOwnerOrReadOnly
from doctors.models import AccessRequest
from families.models import FamilyMember

# Create your views here.
class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['gender']
    ordering_fields = ['id', 'first_name', 'last_name']
    search_fields = ['id', 'first_name', 'last_name', 'contact_number', 'aadhar_number']
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


class VitalsViewSet(viewsets.ModelViewSet):
    serializer_class = VitalsSerializer
    queryset = Vital.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['patient']
    ordering_fields = ['id', 'patient__first_name', 'patient__last_name']
    search_fields = ['id']
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """
        Normal users see only their own record.
        Doctors can see access request approved patient's vitals.
        Family Heads can see their family members' vitals.
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
            patient_id = self.kwargs.get("pk")
            access_requests = AccessRequest.objects.filter(doctor__user=user, patient__id=patient_id,
                                                            is_approved=True)
            if not access_requests.exists():
                return Vital.objects.none()
            return Vital.objects.filter(patient__id=patient_id)
        else:
            return Vital.objects.none()
        
    def get_object(self):
        """
        Override get_object() to retrieve the correct vital record 
        when both patient_id and vital_id are in the URL.
        """
        patient_id = self.kwargs.get("patient_id")
        vital_id = self.kwargs.get("pk")
        try:
            return Vital.objects.get(pk=vital_id, patient_id=patient_id)
        except Vital.DoesNotExist:
            raise PermissionDenied("Vital records not found.")

    def perform_create(self, serializer):
        # Associate the vitals with the patient's record if the user is a patient
        user = self.request.user
        if user.role != 'patient':
            raise PermissionDenied("Only patients are allowed to create vital records.")

        # Check if vital record already exists for this patient
        patient_id = self.kwargs.get("pk")
        if Vital.objects.filter(patient_id=patient_id).exists():
            raise ValidationError({"detail": "Vital records already exists for this patient."})
            
        serializer.save(patient=user.linked_patient)

    def perform_update(self, serializer):
        """
        Allow:
        - patient to update their own vitals
        - doctor to update access request approved patient's vitals
        """
        user = self.request.user
        vital = self.get_object()  # current vital being updated

        # Doctor can update access request approved patient's vitals
        if user.role == "doctor":
            patient_id = self.kwargs.get("patient_id")
            print(patient_id)
            access_requests = AccessRequest.objects.filter(doctor__user=user, patient__id=patient_id,
                                                            is_approved=True)
            if access_requests.exists():
                serializer.save()
                return
            else:
                raise PermissionDenied("You do not have access to update this patient's vitals.")

        # Patient can only update their own vitals
        if user.role == "patient":
            if vital.patient == user.linked_patient:
                serializer.save()
                return
            else:
                raise PermissionDenied("You can only update your own vitals.")

        # All other roles are denied
        raise PermissionDenied("You are not allowed to update vitals.")


class MedicalHistoryViewSet(viewsets.ModelViewSet):
    serializer_class = MedicalHistorySerializer
    queryset = MedicalHistory.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['patient']
    ordering_fields = ['id', 'patient__first_name', 'patient__last_name']
    search_fields = ['id']
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Normal users see only their own record.
        Doctors/labs can see access request approved patient's medical histories.
        Family Heads can see their family members' medical histories.
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
            patient_id = self.kwargs.get("pk")
            access_requests = AccessRequest.objects.filter(doctor__user=user, patient__id=patient_id,
                                                            is_approved=True)
            if not access_requests.exists():
                return MedicalHistory.objects.none()
            return MedicalHistory.objects.filter(patient__id=patient_id)
        else:
            return MedicalHistory.objects.none()
        
    def get_object(self):
        """
        Override get_object() to retrieve the correct vital record 
        when both patient_id and vital_id are in the URL.
        """
        patient_id = self.kwargs.get("patient_id")
        history_id = self.kwargs.get("pk")
        try:
            return MedicalHistory.objects.get(pk=history_id, patient_id=patient_id)
        except MedicalHistory.DoesNotExist:
            raise PermissionDenied("Medical History records not found.")

    def perform_create(self, serializer):
        # Associate the vitals with the patient's record if the user is a patient
        user = self.request.user
        if user.role != 'patient':
            raise PermissionDenied("Only patients are allowed to create medical history.")
    
        serializer.save(patient=user.linked_patient)

    def perform_update(self, serializer):
        """
        Allow:
        - patient to update their own medical histories
        """
        user = self.request.user
        vital = self.get_object()  # current vital being updated

        # Patient can only update their own vitals
        if user.role == "patient":
            if vital.patient == user.linked_patient:
                serializer.save()
                return
            else:
                raise PermissionDenied("You can only update your own medical history.")

        # All other roles are denied
        raise PermissionDenied("You are not allowed to update medical history.")
    
    def perform_destroy(self, instance):
        user = self.request.user
        
        # Only patients can delete
        if user.role != 'patient' or not hasattr(user, 'patient_profile'):
            raise PermissionDenied("Only patients are allowed to delete medical history.")

        patient = user.patient_profile

        # Only the patient who created the medical history can delete it
        if instance.patient != patient:
            raise PermissionDenied("You can only delete medical history you have created.")

        # If all checks pass, delete
        instance.delete()
