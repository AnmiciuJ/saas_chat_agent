from django.contrib import admin

from .models import Plan, Tenant, TenantMembership, UserAccount


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "created_at")
    search_fields = ("code", "name")


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "status", "plan", "contact_email", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "slug", "contact_email")


@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "is_active", "created_at")
    search_fields = ("email",)


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "user_account", "role", "created_at")
    list_filter = ("role",)
