from django.core.exceptions import ObjectDoesNotExist
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import os, base64, re, json, hashlib, hmac

from datetime import datetime

from tenants.models import Account, AccountEncryption
from tenants.local_kms import generate_encrypted_dek, decrypt_dek

from . import etl_postcode
from dotenv import load_dotenv

load_dotenv()

def get_or_create_default_account():
    account, _ = Account.objects.get_or_create(
        name="palmTree",
        short='PALMTREE'
    )
    return account

def resolve_account(tenant_mapping):
    if tenant_mapping:
        account=tenant_mapping.account
    else:
        #use default palmtree account
        account=get_or_create_default_account()
    return account

def get_account_encryption(account):
    account_encryption, created = AccountEncryption.objects.get_or_create(
        account=account,
        defaults={
            "encrypted_dek": generate_encrypted_dek()[1],
            "dek_algorithm": "AES-256-GCM",
            "dek_kms_key_id": "local",  # for local dev
        }
    )
    return account_encryption

DISABLED_ENCR_AND_HMAC=False

def hmac_value(value: str, secret: str) -> str:
    if DISABLED_ENCR_AND_HMAC:
        return f'HMAC({value})'
    else:
        return hmac.new(
            secret.encode(),
            value.encode(),
            hashlib.sha256
        ).hexdigest()

def run_etl_preview(source_fields, canonical_fields, table_data, tenant_mapping=None):
    if not table_data or not table_data.data:
        return []

    header, *rows = table_data.data

    account = resolve_account(tenant_mapping)
    account_encryption = get_account_encryption(account)    
    dek = decrypt_dek(account_encryption.encrypted_dek)
    
    #########################
    #prepare raw data storage
    #########################
    raw_data_storage_rows = []
    for row in rows:
        raw_json_dict=dict(zip(header, row))
        raw_json_dict_not_encrypted=raw_json_dict
        if all(v in (None, "", []) for v in raw_json_dict.values()):
            continue  # skip blank row

        #build raw json with applied pii encryption
        raw_json_dict_enc=encrypt_sensitive_PII_fields_in_place(raw_json_dict, source_fields, account, dek)

        #fingerprints as hmac
        for sf in source_fields:
            if sf.pii_requires_fingerprint:
                orig_field_name = sf.source_field_name
                value = raw_json_dict_not_encrypted.get(orig_field_name)
                field_name = 'FINGERPRINT_'+sf.source_field_name
                #hmac here
                hmac_secret = os.getenv("HMAC_SECRET")
                raw_json_dict_enc[field_name] = hmac_value(value, hmac_secret)

        #finished processing raw row
        raw_data_storage_rows.append(raw_json_dict_enc)

    ##################
    #prepare canonical
    ##################
    canonical_rows = []
    for raw_json_dict in raw_data_storage_rows:
        #build canonical list of values for table
        canonical_row = build_canonical_row(raw_json_dict, canonical_fields, tenant_mapping)
        #finally add all fingerprinted values to canonical
        for sf in source_fields:
            if sf.pii_requires_fingerprint:
                orig_field_name = sf.source_field_name
                value = raw_json_dict_not_encrypted.get(orig_field_name)
                field_name = 'FINGERPRINT_'+sf.source_field_name
                canonical_row[field_name]=raw_json_dict_enc[field_name]

        canonical_rows.append(canonical_row)
    
    ####################
    #prepare for display
    ####################
    display_rows=[]
    for canonical_row in canonical_rows:
        display_row={}
        display_row['TITLE']=decrypt(canonical_row, 'TITLE', account.short, dek)
        display_row['FIRST_NAME']=decrypt(canonical_row, 'FIRST_NAME', account.short, dek)
        display_row['LAST_NAME']=decrypt(canonical_row, 'LAST_NAME', account.short, dek)
        display_row['POSTCODE']=decrypt(canonical_row, 'POSTCODE', account.short, dek)
        
        display_rows.append(display_row)
    
    print (117)
    print (display_rows)

    return canonical_rows, [json.dumps(row) for row in raw_data_storage_rows], display_rows

def decrypt(row, key, short, dek):
    encrypted_value=row[key]
    return decrypt_value(encrypted_value, dek, short)


def encrypt_sensitive_PII_fields_in_place(raw_row, source_fields, account, dek):
    all_kv_values = {}
    for sf in source_fields:
        field_name = sf.source_field_name
        # if sf.pii_requires_encryption:
        #     field_name = 'ENC_'+field_name
        value = raw_row.get(field_name)
        extended_kv_values = apply_normalisation(value, field_name, sf.normalisation)
        k, v = next(iter(extended_kv_values.items()))
        
        try:
            parsed = v
            if isinstance(parsed, dict):
                # Nested JSON found
                for k2, v2 in parsed.items():
                    #encrypt
                    encrypted_value = encrypt(v2, dek, str(account.short)) if sf.pii_requires_encryption and value not in (None, "") else v
                    parsed[k2] = encrypted_value

                    #hash with hmac

                extended_kv_values[k] = parsed
            else:
                #encrypt
                encrypted_value = encrypt(v, dek, str(account.short)) if sf.pii_requires_encryption and value not in (None, "") else v
                extended_kv_values[k] = encrypted_value

                #hash with hmac

        except:
            #encrypt
            encrypted_value = encrypt(v, dek, str(account.short)) if sf.pii_requires_encryption and value not in (None, "") else v
            extended_kv_values[k] = encrypted_value

            #hash with hmac


        for k, v in extended_kv_values.items():
            all_kv_values[k]=v

    return all_kv_values

def encrypt(v, dek, short):
    if DISABLED_ENCR_AND_HMAC:
        return f'ENCR({v})'
    else:
        # ensure bytes
        if isinstance(v, str):
            value_bytes = v.encode("utf-8")
        else:
            value_bytes = v
        # encrypt the bytes
        encrypted_bytes = encrypt_as_aesgcm_with_nonce(dek, value_bytes, short)
        # convert to Base64 string for JSON
        encrypted_value = base64.b64encode(encrypted_bytes).decode("utf-8")
        return encrypted_value


def decrypt_value(encrypted_value, dek, short):
    if DISABLED_ENCR_AND_HMAC:
        # reverse your test wrapper
        if encrypted_value.startswith("ENCR(") and encrypted_value.endswith(")"):
            return encrypted_value[5:-1]
        return encrypted_value
    else:
        # Step 1: base64 decode
        encrypted_bytes = base64.b64decode(encrypted_value)

        # Step 2: decrypt using SAME dek and SAME short
        decrypted_bytes = decrypt_as_aesgcm_with_nonce(
            dek,
            encrypted_bytes,
            short
        )

        # Step 3: convert bytes back to string
        return decrypted_bytes.decode("utf-8")
    
NONCE_SIZE = 12  # standard for AES-GCM

def encrypt_as_aesgcm_with_nonce(dek: bytes, plaintext: bytes, aad: str) -> bytes:
    aesgcm = AESGCM(dek)
    nonce = os.urandom(NONCE_SIZE)
    return nonce + aesgcm.encrypt(nonce, plaintext, aad.encode())
    

def decrypt_as_aesgcm_with_nonce(dek: bytes, encrypted: bytes, aad: str) -> bytes:
    aesgcm = AESGCM(dek)

    # Extract nonce
    nonce = encrypted[:NONCE_SIZE]

    # Extract ciphertext + auth tag
    ciphertext = encrypted[NONCE_SIZE:]

    # Decrypt (will raise InvalidTag if wrong key/aad)
    return aesgcm.decrypt(nonce, ciphertext, aad.encode())


def apply_value_mapping(value, mapping_group):
    if not mapping_group or value is None:
        return value

    value_to_lookup = value

    try:
        mapping = mapping_group.mappings.get(from_code=value_to_lookup)
        return mapping.to_code
    except ObjectDoesNotExist:
        return value  # fallback to original
    
def build_canonical_row(raw_json_row, canonical_fields, tenant_mapping=None):
    all_kv_values = {}
    for cf in canonical_fields:
        sf = cf.source_field
        value = raw_json_row.get(sf.source_field_name)
        # Tenant mapping first (raw → semantic)
        if tenant_mapping and sf.is_tenant_mapping_source:
            kv_value = {cf.name: tenant_mapping.resolve_tenant(value)}
        else:
            # Apply normalisation
            kv_value = apply_normalisation(value, cf.name, cf.normalisation)
            
            # Apply mappings
            if hasattr(cf, "value_mapping_group") and cf.value_mapping_group:
                #kv_value[1] = apply_value_mapping(kv_value[1], cf.value_mapping_group)
                k, v = list(kv_value.items())[0]
                v[k] = apply_value_mapping(v, cf.value_mapping_group)
                kv_value={k: v}

        for k, v in kv_value.items():
            if 'postcode' in cf.format_type:
                #v=json.loads(v)
                all_kv_values[k]=v[cf.format_type]
            else:
                all_kv_values[k]=v
    
    return all_kv_values
    

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

def apply_normalisation(value, field_name, rules):
    if value is None:
        return {field_name: None}

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
                return {field_name: None}

        elif op == "date_format":
            return {field_name: normalise_date(value)}

        elif op == "tri_state_map":
            return {field_name: normalise_opt_in(value)}

        elif op == "trim_whitespace":
            value = re.sub(r"\s+", "", value)
        
        elif op == "parse_postcode":
            json = etl_postcode.parse_uk_postcode(value)
            return json
        
    return {field_name: value}
