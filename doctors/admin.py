from django.contrib import admin
from .models import Doctor, AccessRequest

# Register your models here.
@admin.register(Doctor)
class CustomDoctorsAdmin(admin.ModelAdmin):
    model = Doctor
    list_display = ("id", "name", "hospital", "contact_number")
    list_filter = ("specialty",)

# Register your models here.
@admin.register(AccessRequest)
class CustomAccessRequestAdmin(admin.ModelAdmin):
    model = Doctor
    list_display = ("id", "doctor", "patient", "is_approved", "requested_at")
    list_filter = ("is_approved",)