from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'navbar', NavBarViewSet)
router.register(r'sub_navbar', SubNavBarViewSet)
router.register(r'organization_parent_navbar', OrganizationParentNavBarViewSet)
router.register(r'organization_sub_navbar', OrganizationSubNavBarViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('organization-navbars/<int:org_id>/',
         OrganizationCustomNavBarViewSet.as_view({'get': 'list', 'put': 'update'}),
         name='organization_navbars'),
]
