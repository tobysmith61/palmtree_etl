import re
def run_etl_preview(canonical_fields, field_mappings, table_data, tenant_mapping=None):
    if not table_data or not table_data.data:
        return []

    header, *rows = table_data.data

    # header name → column index
    header_index = {name: i for i, name in enumerate(header)}

    output = []

    for row in rows:
        canonical_row = {}

        for field in canonical_fields:
            source_field = field_mappings.get(field.id)

            if not source_field:
                value = None
            else:
                src_name = source_field.source_field_name
                if src_name not in header_index:
                    value = None
                else:
                    value = row[header_index[src_name]]

            # Tenant mapping
            if tenant_mapping and source_field and source_field.is_tenant_mapping_source:
                value = tenant_mapping.resolve_tenant(value)
            else:
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


