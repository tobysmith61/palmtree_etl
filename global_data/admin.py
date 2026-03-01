from django.contrib import admin
from .models import Marque, Brand
from core.admin_mixins import SoftDeleteAdminMixin


@admin.register(Marque)
class MarqueAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'short')
    search_fields = ('name', 'short')
    ordering = ('name',)


@admin.register(Brand)
class BrandAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'short', 'marque')
    list_filter = ('marque',)
    search_fields = ('name', 'short', 'marque__name')
    ordering = ('marque', 'name')
