from datetime import datetime
from django.db import models

def build_canonical_row(json_row, model_class, fk_map=None):
    """
    Converts a JSON row to a dict ready for Django model creation.
    Automatically handles:
      - Flattening top-level dicts into separate fields if the field exists
      - Foreign keys from fk_map
      - Date parsing
      - Tri-state opt-in normalization
    """
    fk_map = fk_map or {}
    canonical_row = {}

    # Get all concrete model fields
    model_fields = {f.name: f for f in model_class._meta.get_fields()
        if getattr(f, "concrete", False) and not getattr(f, "auto_created", False)}

    for k, v in json_row.items():
        
        # Handle foreign keys
        if k in fk_map:
            canonical_row[k] = fk_map[k]
            continue

        # If v is a dict, try mapping its keys to model fields
        if isinstance(v, dict):
            for sub_key, sub_val in v.items():
                field_name = sub_key  # e.g. postcode_postcode_full
                if field_name in model_fields:
                    canonical_row[field_name] = sub_val
            continue  # skip the top-level dict itself

        # Skip if field doesn't exist in model
        if k not in model_fields:
            continue

        field = model_fields[k]
        
        # Auto-parse dates
        if isinstance(field, (models.DateField, models.DateTimeField)) and isinstance(v, str):
            try:
                v = datetime.strptime(v, "%d/%m/%Y").date()
            except Exception:
                v = None

        # Tri-state flags
        elif getattr(field, "choices", None):
            if v in ["Y", "N"]:
                v = "true" if v == "Y" else "false"
            elif not v:
                v = "missing"
            else:
                v = "unspecified"

        canonical_row[k] = v

    # Fill in any FK fields not in json_row
    for fk_name, fk_val in fk_map.items():
        canonical_row[fk_name] = fk_val

    return canonical_row
