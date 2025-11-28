from django.urls import path
from .views import DoctorViewSet, AccessRequestViewSet, EncounterViewSet, ClinicalNoteViewSet

doctor_list = DoctorViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
doctor_detail = DoctorViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
    'delete': 'destroy',
})

access_request_list = AccessRequestViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
access_request_detail = AccessRequestViewSet.as_view({
    'get': 'retrieve',
    'delete': 'destroy',
})
access_request_verify = AccessRequestViewSet.as_view({
    'post': 'verify_otp',
})
access_request_resend = AccessRequestViewSet.as_view({
    'post': 'resend_otp',
})

# Map specific actions to HTTP verbs
encounter_list = EncounterViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

encounter_detail = EncounterViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
    'delete': 'destroy',
})

# Map specific actions to HTTP verbs
clinical_note_list = ClinicalNoteViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

clinical_note_detail = ClinicalNoteViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
    'delete': 'destroy',
})

urlpatterns = [
    path('', doctor_list, name='doctor-list'),
    path('<int:pk>/', doctor_detail, name='doctor-detail'),

    path('access-requests/', access_request_list, name='access-request-list'),
    path('access-requests/<int:pk>/', access_request_detail, name='access-request-detail'),
    path('access-requests/<int:pk>/verify-otp/', access_request_verify, name='access-request-verify'),
    path('access-requests/<int:pk>/resend-otp/', access_request_resend, name='access-request-resend'),

    path('encounters/', encounter_list, name='encounter-list'),
    path('encounters/<int:pk>/', encounter_detail, name='encounter-detail'),

    path('encounters/clinical-notes/', clinical_note_list, name='clinical-note-list'),
    path('encounters/clinical-notes/<int:pk>/', clinical_note_detail, name='clinical-note-detail'),
]
