from django.urls import path
from .views import PatientViewSet, VitalsViewSet, MedicalHistoryViewSet

# Map HTTP verbs to viewset actions
patient_list = PatientViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

patient_detail = PatientViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',  # use partial_update, not update
})

# Map HTTP verbs to viewset actions
vital_list = VitalsViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

vital_detail = VitalsViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',  # use partial_update, not update
})

# Map HTTP verbs to viewset actions
medical_history_list = MedicalHistoryViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

medical_history_detail = MedicalHistoryViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',  # use partial_update, not update
    'delete': 'destroy',
})

urlpatterns = [
    path('', patient_list, name='patient-list'),
    path('<int:pk>/', patient_detail, name='patient-detail'),

    path('<int:pk>/vitals/', vital_list, name='vital-list'),
    path('<int:patient_id>/vitals/<int:pk>/', vital_detail, name='vital-detail'),

    path('<int:pk>/medical-histories/', medical_history_list, name='medical-history-list'),
    path('<int:patient_id>/medical-histories/<int:pk>/', medical_history_detail, name='medical-history-detail'),
]
