from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Doctor

@receiver(post_save, sender=Doctor)
def update_linked_patient(sender, instance, created, **kwargs):
    if created and instance.user:
        user = instance.user
        if user.role == "doctor" and not user.linked_doctor:
            user.linked_doctor = instance
            user.save(update_fields=["linked_doctor"])
