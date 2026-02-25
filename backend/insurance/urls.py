from django.urls import path
from .views import InsuranceViewSet, InsuranceDocumentViewSet

insurance_list = InsuranceViewSet.as_view({
    "get": "list",
    "post": "create",
})

insurance_detail = InsuranceViewSet.as_view({
    "get": "retrieve",
    "patch": "partial_update",
    "delete": "destroy",
})

document_list = InsuranceDocumentViewSet.as_view({
    "get": "list",
    "post": "create",
})

document_detail = InsuranceDocumentViewSet.as_view({
    "delete": "destroy",
})

urlpatterns = [
    #self route
    path('', insurance_list, name='insurance-list-me'),
    
    #family member route
    path('patient/<int:patient_id>/', insurance_list, name='insurance-list-patient'),
    
    # Detail views
    path('<int:pk>/', insurance_detail, name='insurance-detail'),

    # Documents APIs
    path('<int:insurance_id>/documents/', document_list, name='insurance-document-list'),
    path('<int:insurance_id>/documents/<int:pk>/', document_detail, name='insurance-document-detail'),
]