from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from usuarios.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "created_at")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Metadados", {"fields": ("created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2"),
            },
        ),
    )
