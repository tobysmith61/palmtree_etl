from canonical.models import CanonicalSchema, TableData, Job, FieldMapping, CanonicalField
import json
from django.shortcuts import render, get_object_or_404
from .widgets import ExcelWidget
from .etl import etl_transform
from datetime import date, datetime
from django.contrib import messages

def schema_overview(request):
    """
    List all canonical schemas with buttons linking to their admin pages,
    alongside the source schemas and test data linked to them.
    """
    canonical_schemas = CanonicalSchema.objects.all().select_related(
        "source_schema", "source_schema__table_data"
    )

    schema_list = []
    for cs in canonical_schemas:
        source_schema = getattr(cs, "source_schema", None)  # Safe access
        table_data = getattr(source_schema, "table_data", None) if source_schema else None

        schema_list.append({
            "canonical": cs,
            "source_schema": source_schema,
            "table_data_json": json.dumps(table_data.data if table_data else [])
        })

    return render(request, "canonical/schema_overview.html", {
        "schema_list": schema_list
    })

def serialize_tabledata_for_widget(tabledata_list):
    """
    Convert values to JSON-serializable, preview-friendly representations.
    Dates are wrapped to show storage intent: date(YYYY-MM-DD).
    Nested objects/dicts are converted to JSON strings to avoid [object Object].
    """
    def serialize_value(v):
        if v is None:
            return " "
        if isinstance(v, (date, datetime)):
            return f"date({v.isoformat()})"
        if isinstance(v, (dict, list)):
            # convert nested structures to compact JSON string
            return json.dumps(v, ensure_ascii=False)
        # fallback for other objects: convert to string
        return str(v)

    return [
        [serialize_value(cell) for cell in row]
        for row in tabledata_list
    ]

def strip_empty_rows(table):
    def row_has_data(row):
        return any(
            cell not in (None, "", [])
            and str(cell).strip() != ""
            for cell in row
        )

    return [row for row in table if row_has_data(row)]

def strip_empty_columns(table):
    if not table:
        return table

    # transpose columns
    cols = list(zip(*table))

    def col_has_data(col):
        return any(
            cell not in (None, "", [])
            and str(cell).strip()
            for cell in col
        )

    # keep only columns with data
    kept_cols = [col for col in cols if col_has_data(col)]

    # transpose back
    return [list(row) for row in zip(*kept_cols)]


def canonical_json_to_excel_style_table(canonical_rows):
    # Build canonical table (header + rows)
    if canonical_rows:
        canonical_header = list(canonical_rows[0].keys())
        
        canonical_data = [canonical_header]
        for row in canonical_rows:
            canonical_data.append([row.get(h) for h in canonical_header])
    else:
        canonical_data = [["No mappings"], []]
    canonical_data=strip_empty_columns(strip_empty_rows(canonical_data))
    return canonical_data


def job_preview(request, job_pk):
    while True:
        job = Job.objects.select_related(
            "canonical_schema",
            "source_schema",
            "test_table"
        ).get(pk=job_pk)
        table_data = job.test_table

        if table_data==None:
            messages.error(
                request,
                f"No table data!"
            )
            break
        
        source_data = strip_empty_columns(strip_empty_rows(table_data.data or []))
        source_fields = job.source_schema.field_mappings.all()
        tenant_mapping = None

        canonical_fields = job.canonical_schema.fields.all()

        header, *rows = table_data.data
        raw_json_rows, canonical_rows, display_rows = etl_transform(
            source_fields=source_fields,
            canonical_fields=canonical_fields,
            header=header,
            rows=rows,        
            tenant_mapping=tenant_mapping
        )

        canonical_table_data = canonical_json_to_excel_style_table(canonical_rows)
        display_table_data = canonical_json_to_excel_style_table(display_rows)
        table_widget = ExcelWidget(readonly=True)

        context = {
            "table_data": canonical_table_data,
            "table_source": table_widget.render("table_source", serialize_tabledata_for_widget(source_data)),
            "raw_json_rows": raw_json_rows,
            "table_target": table_widget.render("table_target", serialize_tabledata_for_widget(canonical_table_data)),
            "table_display": table_widget.render("table_display", serialize_tabledata_for_widget(display_table_data)),
        }
        break

    return render(request, "canonical/table_preview.html", context)






from django.shortcuts import render

def hot_demo(request):
    return render(request, "canonical/hot_demo.html")

