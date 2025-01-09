from acr_tool.models import *
from datetime import datetime
from django.utils.timezone import now
from rest_framework import serializers
from utils.s3_utils import upload_file_to_s3_folder


class SecRuleLinksSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecRuleLinks
        fields = ['id', 'rule_name', 'rule_links', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']

    def validate(self, data):
        rule_name = data.get('rule_name')
        rule_links = data.get('rule_links')

        # Ensure rule_links is a list of strings and split them by commas if needed
        if rule_links and isinstance(rule_links, list):
            processed_links = []
            for link in rule_links:
                if isinstance(link, str):
                    # Split each link by commas and strip any leading/trailing spaces
                    processed_links.extend([l.strip() for l in link.split(',')])
                else:
                    raise serializers.ValidationError("Each item in rule_links must be a string.")
            data['rule_links'] = processed_links
        else:
            raise serializers.ValidationError("Rule links must be a list of strings.")

        return data

    def create(self, validated_data):
        instance = SecRuleLinks.objects.create(**validated_data)
        return instance

    def update(self, instance, validated_data):
        instance.rule_name = validated_data.get('rule_name', instance.rule_name)
        instance.rule_links = validated_data.get('rule_links', instance.rule_links)
        instance.save()
        return instance


class RegulatoryRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulatoryRule
        fields = ['rule_order', 'rule_text']

    def validate(self, data):
        # Ensure both fields are provided
        if 'rule_order' not in data:
            raise serializers.ValidationError({"rule_order": "This field is required."})
        if 'rule_text' not in data:
            raise serializers.ValidationError({"rule_text": "This field is required."})
        return data


class RegulatoryReviewSerializer(serializers.ModelSerializer):
    regulatory_rules = RegulatoryRuleSerializer(many=True, required=False)

    class Meta:
        model = RegulatoryReview
        fields = ['id', 'title', 'overview', 'regulatory_rules', 'issue_date', 'section', 'attached_link',
                  'created_by', 'organization', 'created_at']
        read_only_fields = ['id', 'created_by', 'organization', 'created_at']

    def get_regulatory_rules(self, obj):
        # Retrieve and filter related RegulatoryRule objects for the specific RegulatoryReview
        rules = RegulatoryRule.objects.filter(regulatory_review=obj)
        return RegulatoryRuleSerializer(rules, many=True).data

    def to_representation(self, instance):
        # Get the original representation
        representation = super().to_representation(instance)

        # Add or modify any additional fields or data here
        representation['regulatory_rules'] = self.get_regulatory_rules(instance)

        return representation

    def validate(self, data):
        # Ensure that regulatory_rules do not exceed 3 and validate each item
        regulatory_rules_data = data.get('regulatory_rules', [])
        if len(regulatory_rules_data) > 3:
            raise serializers.ValidationError({"regulatory_rules": "You can only provide up to 3 regulatory rules."})

        # Validate each rule in the list
        for rule in regulatory_rules_data:
            if 'rule_order' not in rule:
                raise serializers.ValidationError({"rule_order": "This field is required for each regulatory rule."})
            if 'rule_text' not in rule:
                raise serializers.ValidationError({"rule_text": "This field is required for each regulatory rule."})

            # Ensure rule_order is within the valid range (1 to 3)
            rule_order = rule.get('rule_order')
            if rule_order is not None:
                if not (1 <= rule_order <= 3):
                    raise serializers.ValidationError({"rule_order": "Rule order must be between 1 and 3."})

        return data

    def create(self, validated_data):
        regulatory_rules_data = validated_data.pop('regulatory_rules', [])
        regulatory_review = RegulatoryReview.objects.create(**validated_data)

        for rule_data in regulatory_rules_data:
            RegulatoryRule.objects.create(regulatory_review=regulatory_review, **rule_data)

        # Handle "Final Rules" section logic
        if regulatory_review.section == "Final Rules":
            self.create_or_update_policies_and_procedures(regulatory_review)

        return regulatory_review

    def update(self, instance, validated_data):
        current_year = now().year

        # Check if the instance was created in the current year
        if instance.created_at.year != current_year:
            raise serializers.ValidationError(
                {"error": "You can only update records created in the current year."}
            )

        # Store the old values to compare
        old_title = instance.title
        old_rules = RegulatoryRule.objects.filter(regulatory_review=instance)

        # Update the fields of RegulatoryReview
        instance.title = validated_data.get('title', instance.title)
        instance.overview = validated_data.get('overview', instance.overview)
        instance.issue_date = validated_data.get('issue_date', instance.issue_date)
        instance.section = validated_data.get('section', instance.section)
        instance.attached_link = validated_data.get('attached_link', instance.attached_link)
        instance.save()

        # Update regulatory rules if provided
        regulatory_rules_data = validated_data.get('regulatory_rules')
        if regulatory_rules_data:
            for rule_data in regulatory_rules_data:
                rule_order = rule_data['rule_order']
                rule_text = rule_data['rule_text']

                # Check if a rule with the same order and year exists
                regulatory_rule_obj = RegulatoryRule.objects.filter(
                    regulatory_review=instance,
                    rule_order=rule_order,
                    created_at__year=current_year
                ).first()

                if regulatory_rule_obj:
                    # Update the existing RegulatoryRule
                    regulatory_rule_obj.rule_text = rule_text
                    regulatory_rule_obj.save()
                else:
                    # Create a new RegulatoryRule if it doesn't exist
                    RegulatoryRule.objects.create(
                        regulatory_review=instance,
                        rule_order=rule_order,
                        rule_text=rule_text
                    )

        # Handle the creation of a dummy PoliciesAndProcedures record if title or rules have changed
        if instance.title != old_title or any(rule.rule_text != rule_data.get('rule_text') for rule, rule_data in
                                              zip(old_rules, regulatory_rules_data)):
            # Check if there's a PoliciesAndProcedures record for the given regulatory_review and current year
            if not PoliciesAndProcedures.objects.filter(
                    regulatory_review=instance,
                    created_at__year=current_year
            ).exists():
                # Create a dummy record if it doesn't exist and section is "Final Rules"
                if instance.section == SecRuleLinks.FINAL_RULES:
                    PoliciesAndProcedures.objects.create(
                        regulatory_review=instance,
                        policies_procedure_tab="regulatoryUpdates",
                        organization=instance.organization
                    )

        return instance

    def create_or_update_policies_and_procedures(self, regulatory_review):
        current_year = now().year

        # Check if there's a PoliciesAndProcedures record for the given regulatory_review and current year
        if not PoliciesAndProcedures.objects.filter(
                regulatory_review=regulatory_review,
                created_at__year=current_year
        ).exists():
            # If no record exists for the current year and "Final Rules" section, create a dummy record
            if regulatory_review.section == SecRuleLinks.FINAL_RULES:
                # Create the PoliciesAndProcedures record and set the organization
                PoliciesAndProcedures.objects.create(
                    regulatory_review=regulatory_review,
                    policies_procedure_tab="regulatoryUpdates",
                    organization=regulatory_review.organization  # Set the organization from the regulatory review
                )


class RegulatoryReviewInstructionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegulatoryReviewInstructions
        fields = ['id', 'instructions', 'example', 'created_by', 'created_at']
        read_only_fields = ['created_by', 'created_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        instance.instructions = validated_data.get('instructions', instance.instructions)
        instance.example = validated_data.get('example', instance.example)
        instance.save()
        return instance
