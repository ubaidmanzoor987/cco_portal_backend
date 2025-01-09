from .serializers import *
from django.http import Http404

from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_yasg.inspectors import SwaggerAutoSchema
from navbar.swagger_schema import *


class NavBarViewSet(viewsets.ModelViewSet):
    queryset = NavBar.objects.all()
    serializer_class = NavBarSerializer
    swagger_schema = NavBarSwaggerAutoSchema


class SubNavBarViewSet(viewsets.ModelViewSet):
    queryset = SubNavBar.objects.all()
    serializer_class = SubNavBarSerializer
    swagger_schema = SubNavBarSwaggerAutoSchema


class OrganizationParentNavBarViewSet(viewsets.ModelViewSet):
    queryset = OrganizationParentNavBar.objects.all()
    serializer_class = OrganizationParentNavBarSerializer
    swagger_schema = OrganizationParentNavigationBarSwaggerAutoSchema


class OrganizationSubNavBarViewSet(viewsets.ModelViewSet):
    queryset = OrganizationSubNavBar.objects.all()
    serializer_class = OrganizationSubNavBarSerializer
    swagger_schema = OrganizationSubNavigationBarSwaggerAutoSchema


class OrganizationCustomNavBarViewSet(viewsets.ViewSet):
    serializer_class = NavBarSerializer
    swagger_schema = OrganizationNavigationBarSwaggerAutoSchema

    def list(self, request, org_id=None):
        if org_id:
            parent_navbars = OrganizationParentNavBar.objects.filter(organization_id=org_id)
            parent_serializer = OrganizationParentNavBarSerializer(parent_navbars, many=True).data

            sub_navbars = OrganizationSubNavBar.objects.filter(organization_id=org_id)
            sub_serializer = OrganizationSubNavBarSerializer(sub_navbars, many=True).data

            for parent_navbar in parent_serializer:
                parent_id = parent_navbar['navbar']
                navbar_instance = NavBar.objects.get(id=parent_id)
                parent_navbar['narbar_link'] = navbar_instance.link
                parent_navbar['sub_navbars'] = []
                for sub_navbar in sub_serializer:
                    if sub_navbar['navbar'] == parent_id:
                        sub_navbar_instance = SubNavBar.objects.get(id=sub_navbar['subnavbar'])
                        sub_navbar_link = sub_navbar_instance.link

                        sub_navbar_data = {
                            'id': sub_navbar['id'],
                            'enable': sub_navbar['enable'],
                            'subnavbar': sub_navbar['subnavbar'],
                            'organization': sub_navbar['organization'],
                            'navbar': sub_navbar['navbar'],
                            'subnavbar_name': SubNavBar.objects.get(id=sub_navbar['subnavbar']).name,
                            'subnavbar_display_name': SubNavBar.objects.get(id=sub_navbar['subnavbar']).display_name,
                            'sub_navbar_link': sub_navbar_link
                        }
                        parent_navbar['sub_navbars'].append(sub_navbar_data)

            return Response(parent_serializer)
        else:
            return Response({'status': 'error', 'detail': 'Please provide an org_id parameter.'}, status=400)

    def update(self, request, org_id=None):
        try:
            if not org_id:
                return Http404("Please provide an org_id parameter.")

            request_data = request.data
            for all_navbar in request_data:
                try:
                    organization_parent_navbar = OrganizationParentNavBar.objects.get(id=all_navbar['id'])
                    organization_parent_navbar.enable = all_navbar['enable']  # Update enable field to False
                    organization_parent_navbar.save()
                except OrganizationParentNavBar.DoesNotExist:
                    return Response({
                        'status': 'error',
                        'detail': f'OrganizationParentNavBar with id {all_navbar["id"]} not found.'
                    },
                        status=status.HTTP_404_NOT_FOUND)

                for sub_navbar in all_navbar['sub_navbars']:
                    try:
                        parent_sub_navbar_instance = OrganizationSubNavBar.objects.get(id=sub_navbar['id'])
                        parent_sub_navbar_instance.enable = sub_navbar['enable']
                        parent_sub_navbar_instance.save()
                    except OrganizationSubNavBar.DoesNotExist:
                        return Response({
                            'status': 'error',
                            'detail': f'OrganizationSubNavBar with id {sub_navbar["id"]} not found.'
                        },
                            status=status.HTTP_404_NOT_FOUND)

                    try:
                        sub_navbar_instance = SubNavBar.objects.get(id=sub_navbar['subnavbar'])
                        sub_navbar_instance.name = sub_navbar['subnavbar_name']
                        sub_navbar_instance.link = sub_navbar['sub_navbar_link']
                        sub_navbar_instance.display_name = sub_navbar['subnavbar_display_name']
                        sub_navbar_instance.save()
                    except SubNavBar.DoesNotExist:
                        return Response({
                            'status': 'error',
                            'detail': f'SubNavBar with id {sub_navbar["id"]} not found.'
                        },
                            status=status.HTTP_404_NOT_FOUND)

            return Response({'status': 'success', 'message': 'Organization settings updated successfully.'},
                            status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'status': 'error', 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
