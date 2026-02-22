from django.urls import path
from .views import LabReportViewSet

report_list = LabReportViewSet.as_view({
    "get": "list",
    "post": "create",
})

report_detail = LabReportViewSet.as_view({
    "get": "retrieve",
    "patch": "partial_update",
    "delete": "destroy",
})

urlpatterns = [
    path("<int:patient_id>/",report_list,name="patient-report-list",),
    path("<int:patient_id>/<int:pk>/",report_detail,name="patient-report-detail",),
]
