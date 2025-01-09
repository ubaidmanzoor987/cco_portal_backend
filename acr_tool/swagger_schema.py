from drf_yasg.inspectors import SwaggerAutoSchema


class SecRuleLinksSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Sec Rules']


class RegulatoryReviewSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Regulatory Review']


class RegulatoryReviewInstructionsSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Regulatory Review Instructions']


class RiskAssessmentInstructionsSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Risk Assessment Instructions']


class RiskAssessmentSectionSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Risk Assessment Section']


class RiskAssessmentQuestionSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Risk Assessment Question']


class RiskAssessmentOrgQuestionResponseSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Risk Assessment Org Question Response']


class PoliciesAndProceduresInstructionsSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Policies And Procedures Instructions']


class PoliciesAndProceduresSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Policies And Procedures']


class ProcedureReviewInstructionsSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Procedure Review Instructions']


class ProcedureReviewSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Procedure Review']


class ComplianceMeetingTopicSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Compliance Meeting']


class ComplianceMeetingInstructionsSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Compliance Meeting Instructions']


class ComplianceMeetingSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Compliance Meeting Response']


class AnnualReportSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Annual Report']


class AnnualReportInstructionsSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Annual Report Instructions']

class ARCAllInstructionsSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR All Instructions']

class AWSResourceFileSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR AWS Resource File']


class ConvertPDFToWordSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        return ['ACR Convert PDF To Word']
