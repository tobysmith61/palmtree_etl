from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core import serializers
from pathlib import Path
import json

from django.apps import apps
from core.models import FixtureControlledModel


def dump_fixture(model):
    """Serialize all rows of the model to a pretty-printed JSON fixture."""
    qs = model.objects.all()
    if not qs.exists():
        return

    data = serializers.serialize("json", qs, use_natural_primary_keys=True)
    parsed = json.loads(data)
    pretty_json = json.dumps(parsed, indent=4, sort_keys=True)

    output_dir = Path("fixtures")
    output_dir.mkdir(exist_ok=True)
    filename = output_dir / f"{model._meta.app_label}__{model.__name__}.json"
    filename.write_text(pretty_json, encoding="utf-8")
    print(f"Fixture updated: {filename}")


# Connect to all FixtureControlledModel subclasses
for model in apps.get_models():
    if issubclass(model, FixtureControlledModel) and not model._meta.abstract:
        post_save.connect(lambda sender, **kwargs: dump_fixture(sender), sender=model)
        post_delete.connect(lambda sender, **kwargs: dump_fixture(sender), sender=model)