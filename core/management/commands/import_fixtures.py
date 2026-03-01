from django.core.management.base import BaseCommand
import json
from pathlib import Path
from django.apps import apps
from django.db import transaction
from django.db.models import ForeignKey
from core.models import FixtureControlledModel


class Command(BaseCommand):
    help = "Import all fixtures for FixtureControlledModel subclasses"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            type=str,
            default="fixtures",
            help="Directory where fixture JSON files are located",
        )

    def handle(self, *args, **options):
        fixture_dir = Path(options["dir"])

        for model in apps.get_models():
            if not issubclass(model, FixtureControlledModel) or model._meta.abstract:
                continue

            fixture_file = fixture_dir / f"{model._meta.app_label}__{model.__name__}.json"
            if not fixture_file.exists():
                continue

            with fixture_file.open(encoding="utf-8") as f:
                fixture_data = json.load(f)

            with transaction.atomic():
                for obj in fixture_data:
                    fields = obj["fields"].copy()

                    # Resolve ForeignKey fields
                    for field_name, value in fields.items():
                        field = model._meta.get_field(field_name)
                        if isinstance(field, ForeignKey) and value is not None:
                            related_model = field.remote_field.model
                            # Support natural keys if available
                            if hasattr(related_model, "natural_key_fields") and isinstance(value, (list, tuple)):
                                value = related_model.objects.get(
                                    **dict(zip(related_model.natural_key_fields(), value))
                                )
                            else:
                                value = related_model.objects.get(pk=value)
                            fields[field_name] = value

                    # Determine unique identifier
                    if hasattr(model, "natural_key"):
                        nk_fields = dict(
                            zip(model.natural_key_fields(), model(**fields).natural_key())
                        )
                    else:
                        nk_fields = {"pk": obj["pk"]}

                    # Upsert row
                    model.objects.update_or_create(defaults=fields, **nk_fields)

            self.stdout.write(f"{model._meta.app_label}.{model.__name__}: {len(fixture_data)} rows synced")
            