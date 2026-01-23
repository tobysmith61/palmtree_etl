from django.core.management.base import BaseCommand
from canonical.utils import canonicalise
from canonical.models import SourceSchema, CanonicalSchema

class Command(BaseCommand):
    help = "Test canonicalisation of a sample row"

    def handle(self, *args, **kwargs):
        source_schema = SourceSchema.objects.get(name="Autoline Drive DMS Customer Extract")
        canonical_schema = CanonicalSchema.objects.get(name="DMS_CUSTOMER")

        raw_row = {
            "FIRSTNAME": "Toby",
            "POSTCODE": "sw1a1aa",
            "MAGIC": 123456,
        }

        canonical_json = canonicalise(raw_row, source_schema, canonical_schema)
        self.stdout.write(str(canonical_json))



