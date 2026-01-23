from .models import FieldMapping, CanonicalField, SourceSchema, CanonicalSchema

def canonicalise(raw_row, source_schema, canonical_schema):
    """
    Convert a raw row from a source system into a canonical JSON object
    using the FieldMapping configuration.
    
    :param raw_row: dict of raw data from the source
    :param source_schema: SourceSchema instance
    :param canonical_schema: CanonicalSchema instance
    :return: dict representing canonicalised object
    """
    canonical = {}

    # Get all active mappings for this source schema → canonical schema
    mappings = (
        FieldMapping.objects
        .filter(
            source_schema=source_schema,
            canonical_field__schema=canonical_schema,
            active=True
        )
        .select_related("canonical_field")
        .order_by("order")
    )

    for mapping in mappings:
        source_name = mapping.source_field_name
        target_name = mapping.canonical_field.name

        # Take the raw value and assign to canonical field
        value = raw_row.get(source_name)
        canonical[target_name] = value

    return canonical

import json
import hashlib

def compute_row_hash(row):
    # sort keys to ensure consistent order
    row_json = json.dumps(row, sort_keys=True, separators=(',', ':'))
    return hashlib.md5(row_json.encode('utf-8')).hexdigest()

