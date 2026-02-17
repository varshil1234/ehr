from django.db import models
from patients.models import Patient

class Family(models.Model):
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    head_of_family = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="headed_families",
        db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["head_of_family", "name"],
                name="unique_family_per_head"
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} (Head Patient ID: {self.head_of_family_id})"

class FamilyMember(models.Model):

    RELATION_CHOICES = (
        ("self", "Self"),
        ("parent", "Parent"),
        ("spouse", "Spouse"),
        ("child", "Child"),
        ("sibling", "Sibling"),
        ("other", "Other"),
    )

    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name="members",
        db_index=True
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="family_memberships",
        db_index=True
    )

    relation = models.CharField(
        max_length=20,
        choices=RELATION_CHOICES
    )

    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["family", "patient"],
                name="unique_patient_per_family"
            ),
            models.UniqueConstraint(
                fields=["patient"],
                name="unique_patient_global_family"
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"FamilyMember(Patient={self.patient_id}, Family={self.family_id}, Verified={self.is_verified})"
