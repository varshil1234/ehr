from rest_framework import serializers
from django.utils import timezone
from lab_reports.models import LabReport

class LabReportSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = LabReport
        fields = (
            "id",
            "test_type",
            "lab_name",
            "report_date",
            "status",
            "priority",
            "notes",
            "report_file",   # FILE FIELD ADDED
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    # FILE VALIDATION
    def validate_report_file(self, file):

        if not file:
            return file

        allowed_types = [
            "application/pdf",
            "image/jpeg",
            "image/png",
            "image/jpg"
        ]

        if file.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Only PDF, JPG, or PNG files are allowed."
            )

        max_size = 5 * 1024 * 1024  # 5MB

        if file.size > max_size:
            raise serializers.ValidationError(
                "File size must be under 5MB."
            )

        return file

    # FIELD VALIDATIONS
    def validate_test_type(self, value):

        if value:
            return value

        return value

    def validate_lab_name(self, value):

        if value and len(value.strip()) < 2:
            raise serializers.ValidationError(
                "Lab name must be at least 2 characters."
            )

        if value:
            return value.strip().title()

        return value

    def validate_report_date(self, value):

        if value and value > timezone.now().date():
            raise serializers.ValidationError(
                "Report date cannot be in the future."
            )

        return value

    def validate_notes(self, value):

        if value:
            return value.strip()

        return value

    # OBJECT LEVEL VALIDATION
    def validate(self, attrs):

        request = self.context.get("request")

        if not request or not hasattr(request.user, "patient"):
            raise serializers.ValidationError(
                "Only patients can create reports."
            )

        patient = request.user.patient

        test_type = attrs.get(
            "test_type",
            getattr(self.instance, "test_type", None)
        )

        report_date = attrs.get(
            "report_date",
            getattr(self.instance, "report_date", None)
        )

        lab_name = attrs.get(
            "lab_name",
            getattr(self.instance, "lab_name", None)
        )

        notes = attrs.get(
            "notes",
            getattr(self.instance, "notes", None)
        )

        report_file = attrs.get(
            "report_file",
            getattr(self.instance, "report_file", None)
        )

        # REQUIRE AT LEAST FILE OR DETAILS
        if not report_file and not test_type and not lab_name:
            raise serializers.ValidationError(
                "Upload report file or enter report details."
            )

        # "OTHER" TEST TYPE → NOTES REQUIRED
        if test_type == "other":
            if not notes or not notes.strip():
                raise serializers.ValidationError({
                    "notes": "Notes is required when test type is 'Other'."
                })

        # DUPLICATE PREVENTION
        if test_type and report_date and lab_name:

            qs = LabReport.objects.filter(
                patient=patient,
                test_type=test_type,
                report_date=report_date,
                lab_name__iexact=lab_name
            )

            if self.instance:
                qs = qs.exclude(id=self.instance.id)

            if qs.exists():
                raise serializers.ValidationError(
                    "This report already exists for this patient."
                )

        return attrs
