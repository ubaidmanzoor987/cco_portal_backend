from rest_framework import serializers
from .models import NavBar, SubNavBar, OrganizationParentNavBar, OrganizationSubNavBar


class NavBarSerializer(serializers.ModelSerializer):
    class Meta:
        model = NavBar
        fields = '__all__'


class SubNavBarSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubNavBar
        fields = '__all__'


class OrganizationParentNavBarSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationParentNavBar
        fields = '__all__'


class OrganizationSubNavBarSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationSubNavBar
        fields = '__all__'
