import re
from rest_framework import serializers
from .models import Family, FamilyMember

class FamilySerializer(serializers.ModelSerializer):
    class Meta:
        model = Family
        fields = '__all__'
        read_only_fields = ('head_of_family',)

    # --- Field-level validation for name ---
    def validate_name(self, value):
        """
        Validate that name only contains alphabets, spaces, and basic punctuation.
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Family name cannot be empty or only spaces.")

        # Only allow alphabets, spaces, and hyphens (e.g. 'Shah Family', 'Patel-Kapadia')
        pattern = r'^[A-Za-z\s\-]+$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Family name should only contain letters, spaces, and hyphens."
            )

        # Optional: Capitalize first letter of each word
        return value.strip().title()

    # --- Field-level validation for description ---
    def validate_description(self, value):
        """
        Validate description against a regex pattern if provided.
        Example: must start with a letter and can include letters, numbers, spaces, and punctuation.
        """
        if value:
            pattern = r'^[A-Za-z][A-Za-z0-9\s,.\-!()]*$'
            if not re.match(pattern, value.strip()):
                raise serializers.ValidationError(
                    "Description must start with a letter and can only contain letters, numbers, spaces, and basic punctuation (, . - ! ())."
                )
        return value

    # --- Object-level validation ---
    def validate(self, attrs):
        """
        Prevent a patient from being the head of multiple families.
        """
        head_of_family = attrs.get('head_of_family') or getattr(self.instance, 'head_of_family', None)

        if head_of_family and Family.objects.filter(head_of_family=head_of_family).exclude(id=getattr(self.instance, 'id', None)).exists():
            raise serializers.ValidationError({
                'detail': 'This patient is already the head of another family.'
            })
        return attrs

class FamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyMember
        fields = '__all__'
        read_only_fields = ('is_verified',)

    def validate(self, attrs):
        # Ensure a patient can only be added once per family.
        family = attrs.get('family') or getattr(self.instance, 'family', None)
        patient = attrs.get('patient') or getattr(self.instance, 'patient', None)

        if family and patient:
            exists = FamilyMember.objects.filter(
                family=family,
                patient=patient
            ).exclude(id=getattr(self.instance, 'id', None)).exists()

            if exists:
                raise serializers.ValidationError({
                    'detail': 'This patient is already added as a member of this family.'
                })

        return attrs
