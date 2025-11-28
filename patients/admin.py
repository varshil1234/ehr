from django.contrib import admin
from .models import Patient, Vital, MedicalHistory

@admin.register(Patient)
class CustomPatientAdmin(admin.ModelAdmin):
    model = Patient
    list_display = ("id", "first_name", "last_name", "gender", "contact_number_display")
    list_filter = ("gender",)
    ordering = ("id", "first_name", "last_name")
    search_fields = ("first_name", "last_name", "contact_number", "aadhar_number")
    readonly_fields = ("contact_number_display", "aadhar_display")

    fieldsets = (
        (None, {
            "fields": ("first_name", "last_name", "gender",
                       "date_of_birth", "address", "user",
                       "contact_number_display", "aadhar_display")
        }),
    )

    def contact_number_display(self, obj):
        return obj.contact_number_decrypted or "—"
    contact_number_display.short_description = "Contact Number"

    def aadhar_display(self, obj):
        val = obj.aadhar_number_decrypted
        if val and val != "[Decryption Error]":
            return f"XXXX-XXXX-{val[-4:]}"
        return val or "—"
    aadhar_display.short_description = "Aadhar"


@admin.register(Vital)
class CustomVitalsAdmin(admin.ModelAdmin):
    model = Vital
    list_display = ("id", "patient", "recorded_at")
    readonly_fields = ("recorded_at",)
    list_filter = ("patient__gender",)
    ordering = ("id", "patient__first_name", "patient__last_name")
    search_fields = ("patient__first_name", "patient__last_name", "patient__contact_number", "patient__aadhar_number")

@admin.register(MedicalHistory)
class CustomMedicalHistoryAdmin(admin.ModelAdmin):
    model = MedicalHistory
    list_display = ("id", "patient", "type_of_display", "status_display")
    readonly_fields = (
        "type_of_display", "description_display", "diagnosis_code_display",
        "status_display", "notes_display"
    )
    
    fieldsets = (
        (None, {
            "fields": ("patient", "type_of_display", "description_display", 
                       "diagnosis_code_display", "event_date", "status_display", "notes_display",
                       )
        }),
    )

    def type_of_display(self, obj):
        return obj.type_of_decrypted or "—"
    type_of_display.short_description = "Type Of"

    def description_display(self, obj):
        return obj.description_decrypted or "—"
    description_display.short_description = "Description"

    def diagnosis_code_display(self, obj):
        return obj.diagnosis_code_decrypted or "—"
    diagnosis_code_display.short_description = "Diagnosis Code"

    def status_display(self, obj):
        return obj.status_decrypted or "—"
    status_display.short_description = "Status"

    def notes_display(self, obj):
        return obj.notes_decrypted or "—"
    notes_display.short_description = "Notes"
