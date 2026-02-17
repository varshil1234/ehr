from django.urls import path
from .views import FamilyViewSet, FamilyMemberOTPViewSet,FamilyMemberViewSet

family_list = FamilyViewSet.as_view({
    "get": "list",
    "post": "create",
})

family_detail = FamilyViewSet.as_view({
    "get": "retrieve",
    "patch": "partial_update",
    "delete": "destroy",
})

send_otp = FamilyMemberOTPViewSet.as_view({
    "post": "send_otp"
})

verify_otp = FamilyMemberOTPViewSet.as_view({
    "post": "verify_otp"
})

add_member = FamilyMemberViewSet.as_view({
    "post": "create",
    "get": "list"
})

family_member_detail = FamilyMemberViewSet.as_view({
    "delete": "destroy",    
})

urlpatterns = [
    path("", family_list, name="family-list"),
    path("<int:pk>/", family_detail, name="family-detail"),
    
    path("members/send-otp/", send_otp, name="family-member-send-otp"),
    path("members/verify-otp/", verify_otp, name="family-member-verify-otp"),
    
    path("members/", add_member, name="family-member-add"),
    path("members/<int:pk>/", family_member_detail, name="family-member-detail")
]
