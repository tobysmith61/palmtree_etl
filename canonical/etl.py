import re

def run_etl_preview(tabledata):
    if not tabledata or not tabledata.data:
        return []

    source_schema = tabledata.source_schema
    if not source_schema:
        return []

    header, *rows = tabledata.data

    # Map header name → column index
    header_index = {name: i for i, name in enumerate(header)}

    # Active mappings only, ordered
    mappings = (
        source_schema.field_mappings
        .filter(active=True, canonical_field__isnull=False)
        .select_related("canonical_field")
        .order_by("order")
    )

    output = []

    for row in rows:
        canonical_row = {}

        for mapping in mappings:
            src = mapping.source_field_name
            field = mapping.canonical_field

            if src not in header_index:
                value = None
            else:
                value = row[header_index[src]]

            # Normalise
            value = apply_normalisation(value, field.normalisation)

            canonical_row[field.name] = value

        output.append(canonical_row)

    return output


def normalise_opt_in(value):
    if value is None:
        return 'missing'
    
    value_str = str(value).strip().lower()
    if value_str in ('y', 'yes', 'true', '1'):
        return 'true'
    elif value_str in ('n', 'no', 'false', '0'):
        return 'false'
    elif value_str in ('', 'unknown', 'unspecified'):
        return 'unspecified'
    else:
        return 'unspecified'  # fallback for unexpected values
    
from datetime import datetime


def normalise_date(value):
    if not value:
        return None
    try:
        # Try ISO format first
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        pass
    try:
        # Try European format
        return datetime.strptime(value, '%d/%m/%Y').date()
    except ValueError:
        pass
    # fallback if parsing fails
    return None


def apply_normalisation(value, rules):
    if value is None:
        return None

    for step in rules or []:
        op = step.get("op")

        if op == "trim":
            value = value.strip()

        elif op == "lowercase":
            value = value.lower()

        elif op == "uppercase":
            value = value.upper()

        elif op == "collapse_whitespace":
            value = re.sub(r"\s+", " ", value)

        elif op == "null_if_empty":
            if value == "":
                return None

        elif op == "date_format":
            return normalise_date(value)

        elif op == "tri_state_map":
            return normalise_opt_in(value)

        elif op == "trim_whitespace":
            value = re.sub(r"\s+", "", value)
    
    return value


