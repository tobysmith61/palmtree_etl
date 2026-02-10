import re, json

def run_etl_preview(source_fields, canonical_fields, table_data, tenant_mapping=None):
    if not table_data or not table_data.data:
        return []

    header, *rows = table_data.data
    output = []
    raw_json_enc_rows = []
    for row in rows:
        raw_json_dict=dict(zip(header, row))

        if all(v in (None, "", []) for v in raw_json_dict.values()):
            continue  # skip blank row

        #build raw json with applied pii encryption
        raw_json_dict_enc=encrypt_sensitive_PII_fields_in_place(raw_json_dict, source_fields)
        raw_json_enc_rows.append(json.dumps(raw_json_dict_enc))

        #build canonical list of values for table
        canonical_row = build_canonical_row(raw_json_dict, canonical_fields, tenant_mapping)
        
        print (23)
        print (canonical_row)

        output.append(canonical_row)
    
    return output, raw_json_enc_rows

def encrypt_sensitive_PII_fields_in_place(raw_row, source_fields):
    encrypted_dict = {}
    for sf in source_fields:
        field_name = sf.source_field_name
        value=raw_row[field_name]
        if sf.is_pii and value not in (None, ""):
            encrypted_value = f"encr({value})" # Placeholder encryption for now
        else:
            encrypted_value = value
        encrypted_dict[field_name] = encrypted_value
    return encrypted_dict

def build_canonical_row(raw_json_row, canonical_fields, tenant_mapping=None):
    canonical_row = {}
    for cf in canonical_fields:
        sf = cf.source_field
        value = raw_json_row.get(sf.source_field_name)
        # Tenant mapping first (raw → semantic)
        if tenant_mapping and sf.is_tenant_mapping_source:
            value = tenant_mapping.resolve_tenant(value)
        else:
            value = apply_normalisation(value, cf.normalisation)
        canonical_row[cf.name] = value
    return canonical_row

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


