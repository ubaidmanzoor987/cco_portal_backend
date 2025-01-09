from fiduciary.models import *
from rest_framework import serializers

class GeneralClientRequirementAddSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportGeneralClientRequirement
        fields = ['id','requirement_text']


