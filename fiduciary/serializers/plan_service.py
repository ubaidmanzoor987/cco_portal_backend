from fiduciary.models import *
from rest_framework import serializers



class GeneralPlanServiceAddSerializer(serializers.ModelSerializer):

    class Meta:
        model = GeneralReportPlanService
        fields = ['id','service_name']




