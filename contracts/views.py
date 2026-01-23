from django.shortcuts import render, get_object_or_404
from django.apps import apps
from django.contrib.admin.views.decorators import staff_member_required
from core.models import TimeStampedModel

@staff_member_required
def model_contract_view(request, model_name):
    """
    Display the data contract for a given model name.
    """
    # Find the model dynamically
    model = None
    for m in apps.get_models():
        if m.__name__.lower() == model_name.lower():
            model = m
            break
    if model is None:
        return render(request, "contracts/contract_not_found.html", {"model_name": model_name})

    # Build a set of field names to exclude from TimeStampedModel
    exclude_fields = {f.name for f in TimeStampedModel._meta.fields}
    # Always exclude the default id primary key
    exclude_fields.add('id')

    fields = []
    for field in model._meta.fields:
        if field.name in exclude_fields:
            continue

        fields.append({
            "name": field.name,
            "type": field.get_internal_type(),
            "required": not field.null,
            "primary_key": field.primary_key,
            "max_length": getattr(field, "max_length", None),
            "related_model": field.related_model._meta.label if field.is_relation and field.related_model else None,
        })

    return render(request, "contracts/contract_detail.html", {
        "model_name": model.__name__,
        "app_label": model._meta.app_label,
        "fields": fields,
        "version": "v1",
    })
