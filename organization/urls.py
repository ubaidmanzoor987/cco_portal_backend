from django.urls import path
from .views import *

urlpatterns = [
    path('organization/', OrganizationCreateView.as_view(), name='organization-create'),
    path('organization/<int:pk>/delete/', OrganizationDeleteView.as_view(), name='organization-delete'),
    path('organization/list/', OrganizationListView.as_view(), name='organization-list'),
    path('organization/<int:pk>/', OrganizationRetrieveView.as_view(), name='organization-detail'),
    path('organization/<int:pk>/update/', OrganizationUpdateView.as_view(), name='organization-update'),
    path('organization/users/<int:organization_id>/',
         CustomOrganizationViewSet.as_view({'get': 'users_by_organization'}), name='organization-users'),
    path('basic_templates/upload_files/', BasicTemplateViewSet.as_view({'post': 'upload_files'}),
         name='basic-templates-upload-files'),
]
