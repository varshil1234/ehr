from django.urls import path
from .views import FamilyViewSet, FamilyMemberViewSet

family_list = FamilyViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
family_detail = FamilyViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update',
})

family_member_list = FamilyMemberViewSet.as_view({
    'get': 'list',
    'post': 'create',
})
family_member_detail = FamilyMemberViewSet.as_view({
    'get': 'retrieve',
    'delete': 'destroy',
})

urlpatterns = [
    path('', family_list, name='family-list'),
    path('<int:pk>/', family_detail, name='family-detail'),

    path('members/', family_member_list, name='family-member-list'),
    path('members/<int:pk>/', family_member_detail, name='family-member-detail')
]
