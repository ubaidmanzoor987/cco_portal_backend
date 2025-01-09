from drf_yasg.inspectors import SwaggerAutoSchema


class NavBarSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Navigation Bar']


class SubNavBarSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Sub Navigation Bar']


class OrganizationNavigationBarSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Organization Navigation Bar']


class OrganizationSubNavigationBarSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Organization Sub Navigation Bar']


class OrganizationParentNavigationBarSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Organization Parent Navigation Bar']
