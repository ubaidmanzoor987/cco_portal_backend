from rest_framework import permissions


class IsSuperUser(permissions.BasePermission):
    def has_permission(self, request, view):
        # Check if the user is authenticated first
        if not request.user or not request.user.is_authenticated:
            return False

        # Now you can safely check if the user is a superuser
        return request.user.is_superuser


class IsSuperUserOrCCO(permissions.BasePermission):
    def has_permission(self, request, view):
        # Check if the user is authenticated first
        if not request.user or not request.user.is_authenticated:
            return False

        # Now you can safely check if the user is a superuser or has the CCO role
        return request.user.is_superuser or request.user.role == 'CCO'
