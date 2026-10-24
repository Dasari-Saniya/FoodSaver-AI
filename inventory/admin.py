from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import FoodItem, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile & Role Details'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_role', 'get_organization', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__role')

    @admin.display(description='Role')
    def get_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else '—'

    @admin.display(description='Organization')
    def get_organization(self, obj):
        return obj.profile.organization_name if hasattr(obj, 'profile') else '—'


# Re-register User with custom profile inline
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'organization_name', 'contact_person', 'phone')
    list_filter = ('role',)
    search_fields = ('user__username', 'organization_name', 'contact_person', 'phone')


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'quantity',
        'unit',
        'expiry_date',
        'get_expiry_status',
        'get_waste_risk',
        'added_by',
        'batch_number',
    )
    list_filter = ('category', 'expiry_date')
    search_fields = ('name', 'description', 'donor_info', 'batch_number', 'added_by__username')
    date_hierarchy = 'expiry_date'

    @admin.display(description='Expiry Status')
    def get_expiry_status(self, obj):
        return obj.expiry_status

    @admin.display(description='Waste Risk')
    def get_waste_risk(self, obj):
        return f"{obj.waste_risk_level} ({obj.waste_risk_score}%)"
