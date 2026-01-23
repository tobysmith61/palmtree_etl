# file_ingestion/admin.py
from django.contrib import admin
from .models import IngestedFile

@admin.register(IngestedFile)
class IngestedFileAdmin(admin.ModelAdmin):
    list_display = ("filename", "status", "received_at", "processed_at", "error")
    list_filter = ("status", "received_at", "processed_at")
    search_fields = ("filename", "error")
    readonly_fields = ("received_at", "processed_at")
    ordering = ("-received_at",)
