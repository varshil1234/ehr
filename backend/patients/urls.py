from django.urls import path
from .views import PatientViewSet, PatientVitalsViewSet, MedicalHistoryViewSet, MedicalFollowUpViewSet, FollowUpMedicineViewSet

patient_list = PatientViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

patient_detail = PatientViewSet.as_view({
    'patch': 'partial_update',
})

patient_vitals = PatientVitalsViewSet.as_view({
    "get": "list",
    "post": "create",
})

medical_history_list = MedicalHistoryViewSet.as_view({
    "get": "list",
    "post": "create",
})

medical_history_detail = MedicalHistoryViewSet.as_view({
    "patch": "partial_update",
})

followup_list = MedicalFollowUpViewSet.as_view({
    "get": "list",
    "post": "create",
})

followup_detail = MedicalFollowUpViewSet.as_view({
    "patch": "partial_update",
    "delete": "destroy",
})

medicine_list = FollowUpMedicineViewSet.as_view({
    "get": "list",
    "post": "create",
})

medicine_detail = FollowUpMedicineViewSet.as_view({
    "patch": "partial_update",
    "delete": "destroy",
})

urlpatterns = [
    path('', patient_list, name='patient-list'),
    path('<int:pk>/', patient_detail, name='patient-detail'),
    
    # vitals api
    path("<int:patient_id>/vitals/",patient_vitals,name="patient-vitals"),
    
    # medical history api
    path("<int:pk>/medical-histories/",medical_history_list,name="medical-history-list",),
    path("<int:patient_id>/medical-histories/<int:pk>/",medical_history_detail,name="medical-history-detail",),
    
    path("medical-histories/<int:history_id>/followups/",followup_list,name="followup-list",),
    path("medical-histories/<int:history_id>/followups/<int:pk>/",followup_detail,name="followup-detail",),
    
    #medicine api
    path("medical-histories/<int:history_id>/followups/<int:followup_id>/medicines/",medicine_list,name="medicine-list",),
    path("medical-histories/<int:history_id>/followups/<int:followup_id>/medicines/<int:pk>/",medicine_detail,name="medicine-detail",)
]
