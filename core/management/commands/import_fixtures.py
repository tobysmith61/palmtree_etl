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

        models = [
            m for m in apps.get_models()
            if issubclass(m, FixtureControlledModel) and not m._meta.abstract
        ]

        models = self.sort_models_by_fk_dependency(models)

        for model in models:
            fixture_file = fixture_dir / f"{model._meta.app_label}__{model.__name__}.json"
            if not fixture_file.exists():
                continue

            with fixture_file.open(encoding="utf-8") as f:
                fixture_data = json.load(f)

            with transaction.atomic():
                for obj in fixture_data:
                    fields = obj["fields"].copy()

                    # Assign ForeignKeys using raw _id (no DB lookup)
                    for field_name, value in list(fields.items()):
                        field = model._meta.get_field(field_name)

                        if isinstance(field, ForeignKey) and value is not None:
                            fields[f"{field_name}_id"] = value
                            del fields[field_name]

                    # Determine unique identifier
                    if hasattr(model, "natural_key_fields"):
                        nk_fields = {
                            field: fields[field]
                            for field in model.natural_key_fields()
                        }
                    else:
                        nk_fields = {"pk": obj["pk"]}

                    model.objects.update_or_create(
                        defaults=fields,
                        **nk_fields
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{model._meta.app_label}.{model.__name__}: {len(fixture_data)} rows synced"
                )
            )

    # --------------------------------------------------------
    # Dependency Sorting
    # --------------------------------------------------------

    def sort_models_by_fk_dependency(self, models):
        """
        Topologically sort models so FK dependencies are created first.
        """
        sorted_models = []
        models = set(models)

        while models:
            progressed = False

            for model in list(models):
                dependencies = {
                    field.remote_field.model
                    for field in model._meta.get_fields()
                    if isinstance(field, ForeignKey)
                }

                dependencies = dependencies.intersection(models)

                if not dependencies:
                    sorted_models.append(model)
                    models.remove(model)
                    progressed = True

            if not progressed:
                raise Exception(
                    "Circular dependency detected in fixture models."
                )

        return sorted_models
    