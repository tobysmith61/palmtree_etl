from django.core.management.base import BaseCommand
from django.apps import apps
from django.core import serializers
from pathlib import Path
import json

from core.models import FixtureControlledModel


class Command(BaseCommand):
    help = "List all FixtureControlledModel models and generate pretty-printed JSON fixtures"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            default="fixtures",
            help="Directory where JSON fixtures will be saved",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all concrete subclasses of FixtureControlledModel
        found = [
            model
            for model in apps.get_models()
            if issubclass(model, FixtureControlledModel) and not model._meta.abstract
        ]

        if not found:
            self.stdout.write("No fixture-controlled models found.")
            return

        for model in sorted(found, key=lambda m: (m._meta.app_label, m.__name__)):
            model_label = f"{model._meta.app_label}.{model.__name__}"
            self.stdout.write(f"Processing {model_label}...")

            qs = model.objects.all()
            if not qs.exists():
                self.stdout.write(f"  No rows found, skipping.")
                continue

            # Step 1: Serialize to JSON using Django's JSON serializer
            serialized_data = serializers.serialize(
                "json", qs, use_natural_primary_keys=True
            )

            # Step 2: Load and pretty-print
            parsed = json.loads(serialized_data)
            pretty_json = json.dumps(parsed, indent=4, sort_keys=True)

            # Step 3: Write to file
            filename = output_dir / f"{model._meta.app_label}__{model.__name__}.json"
            filename.write_text(pretty_json, encoding="utf-8")

            self.stdout.write(f"  Fixture saved to {filename}")