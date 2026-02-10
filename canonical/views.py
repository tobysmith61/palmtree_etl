from canonical.models import CanonicalSchema, TableData, Job, FieldMapping, CanonicalField
import json
from django.shortcuts import render, get_object_or_404
from .widgets import ExcelWidget
from .etl import run_etl_preview
from datetime import date


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
    Dates are wrapped to show storage intent: date(YYYY-MM-DD)
    """
    def serialize_value(v):
        if v is None:
            return "NULL"

        if isinstance(v, date):
            return f"date({v.isoformat()})"

        return v

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


def job_preview(request, pk):
    job = Job.objects.select_related(
        "canonical_schema",
        "source_schema",
        "test_table"
    ).get(pk=pk)
    table_data = job.test_table
    source_data = strip_empty_columns(strip_empty_rows(table_data.data or []))
    source_fields = job.source_schema.field_mappings.all()
    canonical_fields = job.canonical_schema.fields.all()
    
    canonical_rows, raw_json_rows = run_etl_preview(
        source_fields=source_fields,
        canonical_fields=canonical_fields,
        table_data=table_data,
    )

    canonical_table_data = canonical_json_to_excel_style_table(canonical_rows)

    source_widget = ExcelWidget(readonly=True)
    target_widget = ExcelWidget(readonly=True)

    context = {
        "tabledata": table_data,
        "table_source": source_widget.render("table_source", serialize_tabledata_for_widget(source_data)),
        "raw_json_rows": raw_json_rows,
        "table_target": target_widget.render("table_target", serialize_tabledata_for_widget(canonical_table_data)),
    }

    return render(request, "canonical/table_preview.html", context)
