from drf_yasg.inspectors import SwaggerAutoSchema


class UsersSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Users']


class AccountSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Account']


class CurrentUserSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Current User']
