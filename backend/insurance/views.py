from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Insurance, InsuranceDocument
from .serializers import InsuranceSerializer, InsuranceDocumentSerializer
from patients.views import get_accessible_patient_ids

class InsuranceViewSet(viewsets.ModelViewSet):
    serializer_class = InsuranceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    #policy ordering options also given
    filter_backends = [OrderingFilter]
    ordering_fields = ['validity_end', 'created_at']
    ordering = ['-validity_end']  

    queryset = Insurance.objects.none()

    def get_queryset(self):
        allowed_ids = get_accessible_patient_ids(self.request.user)
        
        if self.action == 'list':
            patient_id = self.request.query_params.get("patient_id")
            
            if not patient_id:
                raise ValidationError({"patient_id": "Please provide a patient_id to fetch insurances."})
            
            if int(patient_id) not in allowed_ids:
                raise PermissionDenied("You do not have access to this patient's insurance policies.")
            
            qs = Insurance.objects.filter(patient_id=patient_id)

            # is_active filter
            is_active = self.request.query_params.get("is_active")
            if is_active == 'true':
                qs = qs.filter(validity_end__gte=timezone.now().date())
            elif is_active == 'false':
                qs = qs.filter(validity_end__lt=timezone.now().date())

            return qs

        return Insurance.objects.filter(patient_id__in=allowed_ids)

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        allowed_ids = get_accessible_patient_ids(self.request.user)
        if serializer.instance.patient.id not in allowed_ids:
            raise PermissionDenied("You can only update insurance policies for yourself or verified family members.")
        serializer.save()

    def perform_destroy(self, instance):
        allowed_ids = get_accessible_patient_ids(self.request.user)
        if instance.patient.id not in allowed_ids:
            raise PermissionDenied("You can only delete insurance policies for yourself or verified family members.")
        instance.delete()


class InsuranceDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = InsuranceDocumentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def _get_insurance(self):
        user = self.request.user
        insurance_id = self.kwargs.get("insurance_id")
        allowed_ids = get_accessible_patient_ids(user) #same logic here

        
        insurance = Insurance.objects.filter(
            id=insurance_id,
            patient_id__in=allowed_ids
        ).first()

        if not insurance:
            raise PermissionDenied("Not your insurance policy or no permission.")

        return insurance

    def get_queryset(self):
        insurance = self._get_insurance()
        return InsuranceDocument.objects.filter(insurance=insurance)

    def create(self, request, *args, **kwargs):
        insurance = self._get_insurance()
        serializer = self.get_serializer(
            data=request.data,
            context={"insurance": insurance}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        insurance = self._get_insurance()

        if instance.insurance != insurance:
            raise PermissionDenied("Not your document.")

        instance.delete()
        return Response({"detail": "Document deleted"}, status=status.HTTP_204_NO_CONTENT)