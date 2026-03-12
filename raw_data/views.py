from .models import RawCustomerVehicleData
from django.shortcuts import redirect
from django.urls import reverse
from tenants.models import AccountJob
from tenants.views import ensure_local_simulated_sftp_drop_folder
from django.conf import settings
from pathlib import Path
from canonical.etl import etl_transform
from tenants.models import Tenant
import json

def run_account_job_from_django_admin(request, accountjob_pk):
    run_account_job(accountjob_pk)
    return redirect(
        reverse("admin:tenants_accountjob_change", args=[accountjob_pk])
    )

def csv_to_header_and_rows(contents, separator=','):
    lines = contents.splitlines()
    header, *rows = lines
    header = header.split(separator)
    rows = [row.split(separator) for row in rows]
    return header, rows        

tenant_cache = {}
import json
import traceback

tenant_cache = {}

def store_raw_row(raw_json_row, row_number, ready_folder_path, path_and_filename):
    try:
        print(f"\n--- Processing row {row_number} ---")
        print(f"Raw input type: {type(raw_json_row)}")
        print(f"Raw input: {raw_json_row[:200]}...")  # show first 200 chars

        # Convert string to dict
        if isinstance(raw_json_row, str):
            raw_json_row = json.loads(raw_json_row)
        print("Parsed JSON keys:", list(raw_json_row.keys()))

        tenant_code = raw_json_row.get('tenant_code')
        if not tenant_code:
            print("WARNING: tenant_code missing, skipping row")
            return

        # cache tenants to avoid repeated DB lookups
        if tenant_code not in tenant_cache:
            tenant_cache[tenant_code] = Tenant.objects.get(internal_tenant_code=tenant_code)
            print(f"Fetched tenant from DB: {tenant_cache[tenant_code]}")
        else:
            print(f"Using cached tenant: {tenant_cache[tenant_code]}")

        tenant = tenant_cache[tenant_code]

        business_key_hash = raw_json_row.get('business_key_hash')
        row_hash = raw_json_row.get('row_hash')

        if not business_key_hash or not row_hash:
            print("WARNING: business_key_hash or row_hash missing, skipping row")
            return

        # remove these keys from payload
        raw_json_row.pop('tenant_code', None)
        raw_json_row.pop('business_key_hash', None)
        raw_json_row.pop('row_hash', None)

        source_name = "/".join(str(ready_folder_path).strip("/").split("/")[-3:-1])
        print(f"Source name: {source_name}")

        # check for existing current row
        existing = (
            RawCustomerVehicleData.objects
            .filter(
                tenant=tenant,
                business_key_hash=business_key_hash,
                is_current=True
            )
            .first()
        )
        if existing:
            print(f"Existing row found: row_hash={existing.row_hash}, is_current={existing.is_current}")
        else:
            print("No existing row found.")

        # Skip if no change
        if existing and existing.row_hash == row_hash:
            print("Row unchanged, skipping insert.")
            return

        # Retire previous version
        if existing:
            RawCustomerVehicleData.objects.filter(id=existing.id).update(is_current=False)
            print("Retired previous version.")

        # Insert new current version
        rd = RawCustomerVehicleData.objects.create(
            tenant=tenant,
            source_name=source_name,
            business_key_hash=business_key_hash,
            row_hash=row_hash,
            payload=raw_json_row,
            processed=False,
            is_current=True,
            source_file=str(path_and_filename),
            source_row_number=row_number
        )
        print(f"Inserted new row: id={rd.id}, row_hash={rd.row_hash}")

    except Exception as e:
        print("ERROR processing row:")
        print(traceback.format_exc())
        # Optionally: raise e to stop processing, or just log and continue
        
def run_account_job(accountjob_pk):
    accountjob = AccountJob.objects.get(pk=accountjob_pk)

    ready_folder_path = Path(ensure_local_simulated_sftp_drop_folder(settings.BASE_DIR, accountjob))

    for path_and_filename in sorted(ready_folder_path.iterdir()):
        
        print (81)
        print (f'Processing {path_and_filename}')

        with open(path_and_filename, "r") as f:
            contents = f.read()

        header, rows = csv_to_header_and_rows(contents, '|')
        source_fields = accountjob.job.source_schema.field_mappings.all()

        tenant_mapping = accountjob.tenant_mapping
        canonical_fields = accountjob.job.canonical_schema.fields.all()

        raw_json_rows, canonical_rows, display_rows = etl_transform(
            source_fields=source_fields,
            canonical_fields=canonical_fields,
            header=header,
            rows=rows,        
            tenant_mapping=tenant_mapping
        )

        #store raw data
        row_number=0
        for raw_json_row in raw_json_rows:
            row_number+=1
            
            store_raw_row(raw_json_row, row_number, ready_folder_path, path_and_filename)
        
        #store canonical


        #remember to move to processed
    
    
    
    
    return
