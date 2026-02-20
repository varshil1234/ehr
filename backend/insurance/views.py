from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import Insurance, InsuranceDocument
from .serializers import InsuranceSerializer, InsuranceDocumentSerializer

class InsuranceViewSet(viewsets.ModelViewSet):
    serializer_class = InsuranceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    queryset = Insurance.objects.none()

    
    def _get_patient(self):
        user = self.request.user
        if not hasattr(user, "patient"):
            raise PermissionDenied("Only patients can access insurance records.")
        return user.patient


    def get_queryset(self):
        patient = self._get_patient()
        return Insurance.objects.filter(patient=patient)

   
    def perform_create(self, serializer):
        patient = self._get_patient()
        serializer.save(patient=patient)

    def perform_update(self, serializer):
        patient = self._get_patient()
        if serializer.instance.patient != patient:
            raise PermissionDenied("You can only update your own insurance policies.")
        serializer.save()

 
    def perform_destroy(self, instance):
        patient = self._get_patient()
        if instance.patient != patient:
            raise PermissionDenied("You can only delete your own insurance policies.")
        instance.delete()


class InsuranceDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = InsuranceDocumentSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "delete"]

    def _get_insurance(self):
        user = self.request.user
        insurance_id = self.kwargs.get("insurance_id")

        if not hasattr(user, "patient"):
            raise PermissionDenied("Only patients allowed.")

        insurance = Insurance.objects.filter(
            id=insurance_id,
            patient=user.patient
        ).first()

        if not insurance:
            raise PermissionDenied("Not your insurance policy.")

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