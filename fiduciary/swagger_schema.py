from drf_yasg.inspectors import SwaggerAutoSchema

class FiduciaryReportsSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Fiduciary Reports']

class RetrospectiveKeyReviewQuestionSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Fiduciary Retrospective Key Review Question']

class RetrospectiveReviewSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Fiduciary Retrospective Review']

class ReportPlanServicsSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Fiduciary Report Plan Servics']

class ReportClientRequirementSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Fiduciary Report Client Requirement']

class FiduciaryDashboardSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Fiduciary Dashboard']

class FiduciaryReportFileSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Fiduciary Report File']

class FiduciaryAccountsSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['Fiduciary Accounts']