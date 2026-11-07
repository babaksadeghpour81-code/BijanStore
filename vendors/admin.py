from django.contrib import admin
from .models import Vendor


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'legal_name', 'national_id', 'subdomain', 'is_active', 'commission_rate', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'legal_name', 'national_id', 'subdomain')
    prepopulated_fields = {'subdomain': ('name',)}
    readonly_fields = ('created_at',)