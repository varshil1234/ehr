from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Patient

@receiver(post_save, sender=Patient)
def update_linked_patient(sender, instance, created, **kwargs):
    if created and instance.user:
        user = instance.user
        if user.role == "patient" and not user.linked_patient:
            user.linked_patient = instance
            user.save(update_fields=["linked_patient"])
