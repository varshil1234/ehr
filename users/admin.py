from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    ordering = ("email",)
    search_fields = ("email",)

    fieldsets = (
        ('Login Credentials', {'fields': ('email', 'password')}),
        ('Other Details', {'fields': ('date_joined','role', 'linked_patient', 'is_active', 'is_staff')})
    )
    add_fieldsets = (
        ('Login Credentials', {'classes': 'wide', 'fields': ('email', 'password1', 'password2')}),
        ('Other Details', {'fields': ('date_joined', 'role', 'is_active', 'is_staff')})
    )

# Unregister the Group model from the admin site
admin.site.unregister(Group)

admin.site.site_header = "Anantriksh"
admin.site.site_title = "Anantriksh"
admin.site.index_title = "Dashboard"
