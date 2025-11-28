from django.db import models
from patients.models import Patient

# Create your models here.
class Family(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    head_of_family = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='family_head')

    def __str__(self):
        return self.name


class FamilyMember(models.Model):
    RELATIONSHIP_CHOICES = [
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('child', 'Child'),
        ('spouse', 'Spouse'),
        ('other', 'Other'),
    ]
    family = models.ForeignKey(Family, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.patient} member of {self.family}"
