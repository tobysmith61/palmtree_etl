from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from .models import Customer

class DataContractAdminMixin:
    """
    Adds a 'View Data Contract' button to any ModelAdmin
    """

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "contract/",
                self.admin_site.admin_view(self.contract_view),
                name=f"{self.model._meta.app_label}_{self.model._meta.model_name}_contract",
            )
        ]
        return custom_urls + urls

    def contract_view(self, request):
        if not request.user.is_staff:
            raise PermissionDenied

        model = self.model

        fields = []
        for field in model._meta.fields:
            fields.append({
                "name": field.name,
                "type": field.get_internal_type(),
                "required": not field.null,
                "primary_key": field.primary_key,
                "max_length": getattr(field, "max_length", None),
                "related_model": (
                    field.related_model._meta.label
                    if field.is_relation and field.related_model
                    else None
                ),
            })

        context = dict(
            self.admin_site.each_context(request),
            app_label=model._meta.app_label,
            model_name=model.__name__,
            fields=fields,
            version="v1",
        )

        return render(request, "admin/data_contract.html", context)
