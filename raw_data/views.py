from django.shortcuts import redirect
from django.urls import reverse
from tenants.models import AccountJob, AccountJobLog
from tenants.utils import ensure_local_ready_folder
from django.conf import settings
from pathlib import Path
from canonical.etl import etl_transform
from tenants.models import Tenant, TenantMappingCode
import json
from django.utils import timezone
import logging
from pathlib import Path
import shutil
import os
from django.contrib import messages
from canonical.utils import build_canonical_row
from django.db import models, transaction

from .models import RawCustomerVehicleData, RawRecallData, RawBookingData
from contracts.models import Customer, Vehicle, CustomerVehicleLink, Recall, Booking


logger = logging.getLogger(__name__)

tenant_cache = {}


def run_account_job_from_django_admin(request, accountjob_pk):
    accountjob = AccountJob.objects.get(pk=accountjob_pk)
    if accountjob.auto_or_manual=='auto':
        messages.error(request, "Auto or Manual run option needs to be set to Manual")
        return redirect(
            reverse("admin:tenants_accountjob_change", args=[accountjob_pk])
        )
    
    run_account_job(accountjob_pk, request)
    
    return redirect(
        reverse("admin:tenants_accountjob_change", args=[accountjob_pk])
    )

def csv_to_header_and_rows(contents, separator=','):
    lines = contents.splitlines()
    header, *rows = lines
    header = header.split(separator)
    rows = [row.split(separator) for row in rows]
    return header, rows        

def store_raw_row(raw_json_row_dict, row_number, ready_folder_path, path_and_filename, run_id, rawdatamodel, is_tenant_aware):
    try:
        if is_tenant_aware:
            tenant_code = raw_json_row_dict.get('tenant_code')
            if not tenant_code:
                print("WARNING: tenant_code missing, skipping row")
                return

            # cache tenant to avoid repeated DB lookups
            if tenant_code not in tenant_cache:
                tenant_cache[tenant_code] = Tenant.objects.get(internal_tenant_code=tenant_code)
            tenant = tenant_cache[tenant_code]

        business_key_hash = raw_json_row_dict.get('business_key_hash')
        debug_business_key = raw_json_row_dict.get('debug_business_key')

        row_hash = raw_json_row_dict.get('row_hash')

        if not business_key_hash or not row_hash:
            return

        # remove these keys from payload
        if is_tenant_aware:
            raw_json_row_dict.pop('tenant_code', None)
        raw_json_row_dict.pop('business_key_hash', None)
        raw_json_row_dict.pop('row_hash', None)
        raw_json_row_dict.pop('debug_business_key', None)

        source_name = "/".join(str(ready_folder_path).strip("/").split("/")[-3:-1])

        # check for existing current row
        if is_tenant_aware:
            existing = (
                rawdatamodel.objects
                .filter(
                    tenant=tenant,
                    business_key_hash=business_key_hash,
                    is_current=True
                )
                .first()
            )
        else:
            existing = (
                rawdatamodel.objects
                .filter(
                    business_key_hash=business_key_hash,
                    is_current=True
                )
                .first()
            )
       
        # Skip if no change
        if existing and existing.row_hash == row_hash:
            existing.last_seen_run_id = run_id
            existing.save(update_fields=["last_seen_run_id"])
            return "NO_CHANGES"

        # Retire previous version
        if existing:
            rawdatamodel.objects.filter(id=existing.id).update(is_current=False)
            upserted_type="UPDATED"

        # Insert new current version
        if is_tenant_aware:
            rd = rawdatamodel.objects.create(
                tenant=tenant,
                source_name=source_name,
                business_key_hash=business_key_hash,
                debug_business_key=debug_business_key,
                row_hash=row_hash,
                payload=raw_json_row_dict,
                processed=False,
                is_current=True,
                source_file=str(path_and_filename),
                source_row_number=row_number,
                last_seen_run_id = run_id,
            )
        else:
            rd = rawdatamodel.objects.create(
                source_name=source_name,
                business_key_hash=business_key_hash,
                debug_business_key=debug_business_key,
                row_hash=row_hash,
                payload=raw_json_row_dict,
                processed=False,
                is_current=True,
                source_file=str(path_and_filename),
                source_row_number=row_number,
                last_seen_run_id = run_id,
            )
        print(f"Inserted new row: id={rd.id}, row_hash={rd.row_hash}")
        upserted_type="INSERTED"
        return upserted_type
    
    except Exception as e:
        print("ERROR processing row:")
        # Optionally: raise e to stop processing, or just log and continue
        raise






def get_unique_fields(model):
    """
    Extract the first UniqueConstraint fields from the model.

    Assumes:
    - You have at least one UniqueConstraint defined
    - That constraint defines how we identify "same row"
    """
    for constraint in model._meta.constraints:
        if isinstance(constraint, models.UniqueConstraint):
            return constraint.fields

    raise ValueError(f"No UniqueConstraint found on {model.__name__}")

def map_string_model_to_django_model(string_model):
    if string_model=='contracts.Customer':
        return Customer
    elif string_model=='contracts.Vehicle':
        return Vehicle
    elif string_model=='contracts.CustomerVehicleLink':
        return CustomerVehicleLink
    elif string_model=='contracts.Recall':
        return Recall
    elif string_model=='contracts.Booking':
        return Booking
    
    elif string_model=='RawCustomerVehicleData':
        return RawCustomerVehicleData
    elif string_model=='RawRecallData':
        return RawRecallData
    elif string_model=='RawBookingData':
        return RawBookingData
    
    else:
        1/0

@transaction.atomic
def sync_model_from_canonical(accountjob, canonical_rows, build_row_fn):
    """
    Perform a FULL SYNC between canonical data and a Django model.

    This will:
    - CREATE new rows
    - UPDATE existing rows
    - DELETE rows not present in canonical_rows

    Parameters:
    ----------
    accountjob : AccountJob instance
        Contains account, job, and tenant mapping info.

    canonical_rows : iterable of dicts
        Raw input data from source system.

    build_row_fn : function
        Function that converts canonical_row → model-ready dict.

    Returns:
    -------
    dict with counts of created/updated/deleted
    """

    # Map contract string → Django model class
    model = map_string_model_to_django_model(accountjob.job.canonical_schema.contract)

    # 🔑 Determine fields that uniquely identify a row (for update/delete)
    unique_fields = get_unique_fields(model)
    if accountjob.tenant_mapping!=None:
        # -----------------------------------
        # 1️⃣ Load scoped tenants for this job
        # -----------------------------------
        # Get Tenant instances from the tenant mapping
        tenant_map = {
            t.mapped_tenant.internal_tenant_code: t.mapped_tenant
            for t in accountjob.tenant_mapping.mapping_codes.all()
        }

        # Extract primary keys of tenants (your Tenant PK is internal_tenant_code)
        scoped_tenant_pks = list(tenant_map.keys())

        # -----------------------------------
        # 2️⃣ Load existing rows in DB
        # -----------------------------------
        # Filter by tenants included in this job
        existing_qs = model.objects.filter(tenant__internal_tenant_code__in=scoped_tenant_pks)
    else:
        existing_qs = model.objects.all()

    # Map existing rows by their unique key for quick lookup
    existing_map = {}
    
    # normalise key for comparison to ident if new or existing
    for obj in existing_qs:
        key = tuple(
            getattr(obj, f).internal_tenant_code
            if f.endswith("tenant")
            else getattr(obj, f)
            for f in unique_fields
        )

        key = tuple(
            str(v) if type(v) is int else v
            for v in key
        )

        existing_map[key] = obj
    
    # Track which keys are seen in canonical_rows
    seen_keys = set()

    # Prepare lists for bulk operations
    to_create = []
    to_update = []

    # -----------------------------------
    # 3️⃣ Process canonical rows
    # -----------------------------------
    unchanged_count=0
    for row in canonical_rows:
        
        fk_map = {}
        if "tenant" in row:
            tenant_code = row["tenant"]
            fk_map["tenant"] = tenant_map[tenant_code]

        data = build_row_fn(row, model, fk_map=fk_map)

        key = tuple(
            data[f].internal_tenant_code if isinstance(data[f], Tenant) else data[f]
            for f in unique_fields
        )

        seen_keys.add(key)
        if key in existing_map:
            obj = existing_map[key]

            has_changed = False
            if obj.row_hash != data['row_hash']:
                has_changed = True

            if has_changed:
                for field, value in data.items():
                    setattr(obj, field, value)
                to_update.append(obj)
            else:
                unchanged_count += 1
        else:
            to_create.append(model(**data))



    # -----------------------------------
    # 4️⃣ Delete rows not present in canonical_rows
    # -----------------------------------
    to_delete = [
        obj for key, obj in existing_map.items()
        if key not in seen_keys
    ]

    # -----------------------------------
    # 5️⃣ Bulk database operations
    # -----------------------------------
    if to_create:
        model.objects.bulk_create(to_create, batch_size=1000)

    if to_update:
        update_fields = list(data.keys())
        
        
        model.objects.bulk_update(to_update, update_fields, batch_size=1000)

    if to_delete:
        model.objects.filter(
            **{"pk__in": [obj.pk for obj in to_delete]}
        ).delete()

    return {
        "created": len(to_create),
        "updated": len(to_update),
        "deleted": len(to_delete),
        "unchanged": unchanged_count,
    }

def validate_header(header, source_fields):
    if not header:
        logger.error("Header is empty or None")
        return False

    if not source_fields:
        logger.error("Source fields is empty or None")
        return False

    # normalize CSV header (strings)
    header_set = {str(h).strip().lower() for h in header}

    # IMPORTANT: extract field names from FieldMapping objects
    required_set = {
        str(f.source_field_name).strip().lower()
        for f in source_fields
    }

    missing = required_set - header_set

    if missing:
        logger.error(
            "Missing required columns=%s | found=%s",
            sorted(missing),
            sorted(header_set),
        )
        return False

    return True

def run_account_job(accountjob_pk, request=None):
    logger.info(f"Starting run_account_job for pk={accountjob_pk}")
    accountjob = AccountJob.objects.get(pk=accountjob_pk)

    if not accountjob.job:
        logger.info(f"Improperly configured account_job {accountjob}: No Job provided")
    if not accountjob.sftp_drop_zone:
        logger.info(f"Improperly configured account_job {accountjob}: No sFTP Drop Zone")
    
    ready_folder_path = Path(
        ensure_local_ready_folder(accountjob)
    )

    logger.info(f"Ready folder: {ready_folder_path}")

    #################################################################
    # for each file currently in the ready folder awaiting processing
    #################################################################
    for path_and_filename in sorted(ready_folder_path.iterdir()):
        if not path_and_filename.is_file() or not path_and_filename.name.startswith(accountjob.job.source_schema.filename_prefix):
            continue

        logger.info(f"Processing file: {path_and_filename}")

        last_seen_run_id = timezone.now().strftime("%Y-%m-%d_%H-%M-%S")

        with open(path_and_filename, "r") as f:
            contents = f.read()

        header, rows = csv_to_header_and_rows(contents, '|')

        logger.debug(f"Header: {header}")
        logger.debug(f"Row count: {len(rows)}")

        source_fields = accountjob.job.source_schema.field_mappings.all()

        if not validate_header(header, source_fields):
            failed_path = path_and_filename.parent.parent / "failed" / path_and_filename.name
            if os.environ.get("IS_STAGING_SERVER") == "True":
                os.makedirs(failed_path, exist_ok=True)

            shutil.move(path_and_filename, failed_path)
            continue

        tenant_mapping = accountjob.tenant_mapping
        canonical_fields = accountjob.job.canonical_schema.fields.all()

        ############
        # do the etl
        ############
        raw_json_rows, canonical_rows, _ = etl_transform(
            source_fields=source_fields,
            canonical_fields=canonical_fields,
            orig_header=header,
            orig_rows=rows,
            tenant_mapping=tenant_mapping,
            prepare_for_display=False,
        )
        logger.info(f"Transformed rows: {len(raw_json_rows)}")

        ################
        # store raw rows
        ################

        # get model
        rawdatamodel = map_string_model_to_django_model(accountjob.job.source_schema.raw_data_storage_model)
        
        # get current
        is_tenant_aware = accountjob.tenant_mapping != None

        if is_tenant_aware:
            tenants = accountjob.tenant_mapping.mapping_codes.all() # the 'expected' scope of the tenants
            existing_keys = set(
                rawdatamodel.objects.filter(
                    tenant__in=tenants.values_list('mapped_tenant_id', flat=True),
                    is_current=True
                ).values_list('business_key_hash', flat=True)
            )
        else:
            existing_keys = set(
                rawdatamodel.objects.filter(
                    is_current=True
                ).values_list('business_key_hash', flat=True)
            )

        # insert new versions
        seen_keys = set()
        row_number = 0
        for raw_json_row in raw_json_rows:
            row_number += 1

            # Convert string to dict
            if isinstance(raw_json_row, str):
                raw_json_row_dict = json.loads(raw_json_row)

            key = raw_json_row_dict.get('business_key_hash')
            seen_keys.add(key)
            
            result = store_raw_row(
                raw_json_row_dict,
                row_number,
                ready_folder_path,
                path_and_filename,
                last_seen_run_id,
                rawdatamodel,
                is_tenant_aware
            )

            #logger.debug(f"Row {row_number} store result: {result}")

            if result in ["INSERTED", "UPDATED"]:
                pass

        # flag omitted items as deleted_at_source
        missing_keys = existing_keys - seen_keys
        
        if is_tenant_aware:
            rawdatamodel.objects.filter(
                tenant__in=tenants.values_list('mapped_tenant_id', flat=True),
                is_current=True,
                business_key_hash__in=missing_keys
            ).update(
                is_deleted_at_source=True,
            )
        else:
            rawdatamodel.objects.filter(
                is_current=True,
                business_key_hash__in=missing_keys
            ).update(
                is_deleted_at_source=True,
            )

        ######################
        # store canonical rows
        ######################
        result = sync_model_from_canonical(accountjob, canonical_rows, build_canonical_row)

        if accountjob.move_source_file_on_completion:
            #move the file from /ready to /processed        
            processed_path = path_and_filename.parent.parent / "processed" / path_and_filename.name
            if os.environ.get("IS_STAGING_SERVER") == "True":
                os.makedirs(processed_path, exist_ok=True)

            shutil.move(path_and_filename, processed_path)

        logger.info("Finished file processing")

        result_text = f"Job complete, Canonical results: Created: {result['created']}, Updated: {result['updated']}, Deleted: {result['deleted']}, Unchanged: {result['unchanged']}"
        if request:
            messages.info(
                request,
                result_text
            )

        log = AccountJobLog()
        log.account = accountjob.account
        log.accountjob = accountjob
        log.result_text = result_text
        log.path_and_filename = path_and_filename
        log.save()

    logger.info("Job complete")

    return



#next: test deletion followed by re-insertion, need to know and understand behaviour currently, scenarios and requirements
