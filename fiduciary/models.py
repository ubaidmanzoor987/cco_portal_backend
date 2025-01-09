from django.db import models
from django.contrib.auth.models import User
from accounts.models import CustomUser
import uuid
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class FiduciaryReport(models.Model):
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reports')
    notes = models.TextField(blank=True, null=True)
    is_draft = models.BooleanField(default=False,blank=True, null=True)
    
   
    disclosures_delivered = models.BooleanField(default=False, verbose_name="Disclosures Delivered?",blank=True, null=True)
    alternative_plans_presented = models.BooleanField(default=False, verbose_name="Alternative Plans Presented?",blank=True, null=True)
    fee_services_analysis = models.BooleanField(default=False, verbose_name="Fee & Services Analysis?",blank=True, null=True)
    best_interest_recommendation = models.BooleanField(default=False, verbose_name="Recommendation in the best interest of the client?",blank=True, null=True)
    
    cover_page = models.TextField(blank=True, null=True, verbose_name="Cover Page")
    introduction_page = models.TextField(blank=True, null=True, verbose_name="Introduction Page")
    disclosures = models.TextField(blank=True, null=True, verbose_name="Disclosures")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    s3_file_link = models.CharField(max_length=255,blank=True, null=True)
    

    def __str__(self):
        return f"{self.s3_file_link}" 


class ReportClientDetails(models.Model):
    
    TYPE_OF_CLIENT_CHOICES = [
        ('New', 'New'),
        ('Current', 'Current'),
        ('Former', 'Former'),
    ]
    
    RISK_TOLERANCE_CHOICES = [
        ('Aggressive', 'Aggressive'),
        ('Moderate', 'Moderate'),
        ('Conservative', 'Conservative'),
    ]

    INVESTMENT_OBJECTIVE_CHOICES = [
        ('Growth', 'Growth'),
        ('Income', 'Income'),
        ('Preservation', 'Preservation'),
        ('Growth & Income', 'Growth & Income'),
    ]
    
    CLIENT_GOALS_CHOICES = [
        ('Retirement', 'Retirement'),
        ('Travel', 'Travel'),
        ('Hobbies', 'Hobbies'),
        ('Accumulation', 'Accumulation'),
        ('Education', 'Education'),
        ('Estate Planning', 'Estate Planning'),
        ('Real Estate', 'Real Estate'),
    ]

    REASON_FOR_ROLLOVER_CHOICES = [
        ('Plan Termination', 'Plan Termination'),
        ('Transfer', 'Transfer'),
        ('Retired', 'Retired'),
    ]
    
    TIMELINE_CHOICES = [
        ('0-5 Years', '0-5 Years'),
        ('5-10 Years', '5-10 Years'),
        ('10-15 Years', '10-15 Years'),
        ('15+ Years', '15+ Years'),
    ]
    
    TYPE_OF_PLAN_CHOICES = [
        ('Plan to IRA', 'Plan to IRA'),
        ('IRA to IRA', 'IRA to IRA')  
    ]

    fiduciaryreport = models.OneToOneField('FiduciaryReport', on_delete=models.CASCADE, related_name='client_details')
    first_name = models.CharField(blank=True, null=True,max_length=100)
    last_name = models.CharField(blank=True, null=True,max_length=100)
    client_email = models.EmailField(blank=True, null=True,)
    date_of_birth = models.DateField(blank=True, null=True,)
    advisor_full_name = models.CharField(blank=True, null=True,max_length=255)
    date_prepared = models.DateField(blank=True, null=True)

    type_of_client = models.CharField(blank=True, null=True,max_length=50, choices=TYPE_OF_CLIENT_CHOICES)
    client_risk_tolerance = models.CharField(blank=True, null=True,max_length=50, choices=RISK_TOLERANCE_CHOICES)
    investment_objective = models.CharField(blank=True, null=True,max_length=50, choices=INVESTMENT_OBJECTIVE_CHOICES)
    timeline = models.CharField(blank=True, null=True,max_length=50, choices=TIMELINE_CHOICES)
    type_of_plan = models.CharField(blank=True, null=True,max_length=100, choices=TYPE_OF_PLAN_CHOICES)
    reason_for_rollover = models.CharField(blank=True, null=True,max_length=50, choices=REASON_FOR_ROLLOVER_CHOICES)
    client_goals = models.CharField(blank=True, null=True,max_length=50, choices=CLIENT_GOALS_CHOICES)

    advisor_notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.fiduciaryreport.id}"


class ReportResourcesReviewed(models.Model):
    
    fiduciaryreport = models.OneToOneField('FiduciaryReport', on_delete=models.CASCADE, related_name='resources_reviewed')

    plan_fee_data = models.BooleanField(default=False, verbose_name='404(a) Plan and Fee Data')
    form_5500 = models.BooleanField(default=False, verbose_name='Form 5500')
    benchmark_data = models.BooleanField(default=False, verbose_name='Benchmark Data')
    quarterly_account_statements = models.BooleanField(default=False, verbose_name='Quarterly Account Statements')
    summary_plan_description = models.BooleanField(default=False, verbose_name='Summary Plan Description')
    investment_comparative_chart = models.BooleanField(default=False, verbose_name='Investment Comparative Chart')
    ips = models.BooleanField(default=False, verbose_name='IPS')
  
    other_description = models.TextField(blank=True, null=True, verbose_name="Other, Please Describe Below")
    additional_document_links = ArrayField(models.URLField(), blank=True, default=list)

    def __str__(self):
        return f"Resources Reviewed for Report {self.fiduciaryreport.id}"


class ReportGeneralClientRequirement(models.Model):
    requirement_text = models.TextField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_client_requirements')
   
    def __str__(self):
        return f"{self.requirement_text}"


class ReportClientRequirements(models.Model):
    RESPONSE_CHOICES = [
        ('Yes', 'Yes'),
        ('No', 'No'),
        ('Uncertain', 'Uncertain'),
    ]

    fiduciaryreport = models.ForeignKey(FiduciaryReport, on_delete=models.CASCADE, related_name='client_requirements')  
    general_requirement = models.ForeignKey(ReportGeneralClientRequirement, on_delete=models.CASCADE, related_name='general_client_requirements',blank=True, null=True)  
    status = models.CharField(max_length=10, choices=RESPONSE_CHOICES, verbose_name="status",blank=True, null=True)  
    notes = models.TextField(blank=True, null=True) 
    #def __str__(self):
        #return f"Requirement: {self.general_requirement.requirement_text} - Status: {self.status} for Report {self.fiduciaryreport.id}"

class GeneralReportPlanService(models.Model):
    service_name = models.CharField(max_length=255,null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_plan_services')
    
    def __str__(self):
        return f"{self.service_name}" 


class ReportPlanServices(models.Model):
    fiduciaryreport = models.ForeignKey(FiduciaryReport, on_delete=models.CASCADE, related_name='plan_services')
    general_plan_service = models.ForeignKey(GeneralReportPlanService, on_delete=models.SET_NULL, null=True, blank=True, related_name='report_plan_services')
    current_plan = models.BooleanField(default=False,null=True, blank=True,)
    recommended_ira = models.BooleanField(default=False,null=True, blank=True,)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.general_plan_service.service_name} for Report {self.fiduciaryreport.id}" if self.general_plan_service else f"Service for Report {self.fiduciaryreport.id}"
    

class  ReportCostComparison(models.Model):
    fiduciaryreport = models.OneToOneField(FiduciaryReport, on_delete=models.CASCADE, related_name='cost_comparison')

    # Current Plan fields
    current_plan_type = models.CharField(max_length=255, verbose_name='Type of Account (Current Plan)', blank=True, null=True)
    current_account_value = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Account Value (Current Plan)', blank=True, null=True)
    current_aum_fee = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='AUM Fee % (Current Plan)', blank=True, null=True)
    current_expenses = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Expenses % (Current Plan)', blank=True, null=True)
    current_total_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Total Current Cost', blank=True, null=True)

    # Recommended IRA fields
    recommended_plan_type = models.CharField(max_length=255, verbose_name='Type of Account (Recommended IRA)', blank=True, null=True)
    recommended_account_value = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Account Value (Recommended IRA)', blank=True, null=True)
    recommended_aum_fee = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='AUM Fee % (Recommended IRA)', blank=True, null=True)
    recommended_expenses = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Expenses % (Recommended IRA)', blank=True, null=True)
    recommended_total_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Total New Cost', blank=True, null=True)

    # Value justification
    value_justification = models.BooleanField(default=False, verbose_name='Does the value justify the fees for the recommended IRA?')

    # Additional notes
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Cost Comparison for Report {self.fiduciaryreport.id}"



class  ReportNewPlanRecommendation(models.Model):
    fiduciaryreport = models.OneToOneField(FiduciaryReport, on_delete=models.CASCADE, related_name='plan_recommendations')

    # Proposed Plan Fields
    proposed_ira_name = models.CharField(max_length=255, verbose_name='Name of Proposed IRA', blank=True, null=True)
    proposed_total_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Total Costs', blank=True, null=True)
    proposed_avg_rate_of_return = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Average Rate of Return', blank=True, null=True)
    proposed_investments_available = models.CharField(max_length=255, verbose_name='Investments Available', blank=True, null=True)
    proposed_risk_category = models.CharField(max_length=255, verbose_name='Risk Category', blank=True, null=True)
    
    # Peer 1 Plan Fields
    peer1_ira_name = models.CharField(max_length=255, verbose_name='Name of Peer 1 IRA', blank=True, null=True)
    peer1_total_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Total Costs (Peer 1)', blank=True, null=True)
    peer1_avg_rate_of_return = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Average Rate of Return (Peer 1)', blank=True, null=True)
    peer1_investments_available = models.CharField(max_length=255, verbose_name='Investments Available (Peer 1)', blank=True, null=True)
    peer1_risk_category = models.CharField(max_length=255, verbose_name='Risk Category (Peer 1)', blank=True, null=True)
    
    # Peer 2 Plan Fields
    peer2_ira_name = models.CharField(max_length=255, verbose_name='Name of Peer 2 IRA', blank=True, null=True)
    peer2_total_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Total Costs (Peer 2)', blank=True, null=True)
    peer2_avg_rate_of_return = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Average Rate of Return (Peer 2)', blank=True, null=True)
    peer2_investments_available = models.CharField(max_length=255, verbose_name='Investments Available (Peer 2)', blank=True, null=True)
    peer2_risk_category = models.CharField(max_length=255, verbose_name='Risk Category (Peer 2)', blank=True, null=True)
    
    # Peer 3 Plan Fields
    peer3_ira_name = models.CharField(max_length=255, verbose_name='Name of Peer 3 IRA', blank=True, null=True)
    peer3_total_cost = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Total Costs (Peer 3)', blank=True, null=True)
    peer3_avg_rate_of_return = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Average Rate of Return (Peer 3)', blank=True, null=True)
    peer3_investments_available = models.CharField(max_length=255, verbose_name='Investments Available (Peer 3)', blank=True, null=True)
    peer3_risk_category = models.CharField(max_length=255, verbose_name='Risk Category (Peer 3)', blank=True, null=True)

    # Value Proposition
    value_proposition = models.TextField(blank=True, null=True, verbose_name="Firm's Value Proposition")

    # Why this selection is in the client's best interest
    best_interest_reason = models.TextField(blank=True, null=True, verbose_name="Why is this Selection in the Best Interest of the Client?")

    def __str__(self):
        return f"New Plan Recommendation for Report {self.fiduciaryreport.id}"


class RetrospectiveKeyReviewQuestion(models.Model):
    question_text = models.CharField(max_length=255)
    is_required = models.BooleanField(default=True)

    def __str__(self):
        return self.question_text


class RetrospectiveKeyReviewAnswer(models.Model):
    question = models.ForeignKey(RetrospectiveKeyReviewQuestion, on_delete=models.CASCADE)
    answer = models.BooleanField(default=False)
    year_of_report = models.PositiveIntegerField(blank=True, null=True)  
    notes = models.TextField(blank=True, null=True)
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='review_answers', blank=True, null=True)

    def __str__(self):
        return f"Answer to '{self.question.question_text}' for year {self.year_of_report}"



def get_expiration_date():
    return timezone.now() + timezone.timedelta(days=3)

class SignUpInvitation(models.Model):
    email = models.EmailField(unique=True)
    secret_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_used = models.BooleanField(default=False)
    expiration_date = models.DateTimeField(default=get_expiration_date)
