# core/admin/fixture_signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core import serializers
from pathlib import Path
import json

from django.apps import apps
from core.models import FixtureControlledModel


def dump_fixture(model, output_dir="fixtures"):
    """
    Serialize all rows of the model to a pretty-printed JSON fixture,
    sorted by PK to make output deterministic.
    """
    qs = model.objects.all().order_by("pk")  # always PK order
    if not qs.exists():
        return

    # Serialize to JSON using natural keys if available
    data = serializers.serialize("json", qs, use_natural_primary_keys=True)
    parsed = json.loads(data)

    # Sort parsed JSON rows by PK (or you could sort by natural key)
    parsed.sort(key=lambda obj: obj["pk"])

    # Pretty-print JSON and sort fields alphabetically
    pretty_json = json.dumps(parsed, indent=4, sort_keys=True)

    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Filename: appname__ModelName.json (double underscore)
    filename = output_path / f"{model._meta.app_label}__{model.__name__}.json"
    filename.write_text(pretty_json, encoding="utf-8")

    print(f"Fixture updated: {filename}")


# Connect to all FixtureControlledModel subclasses in all apps
for model in apps.get_models():
    if issubclass(model, FixtureControlledModel) and not model._meta.abstract:
        post_save.connect(lambda sender, **kwargs: dump_fixture(sender), sender=model)
        post_delete.connect(lambda sender, **kwargs: dump_fixture(sender), sender=model)