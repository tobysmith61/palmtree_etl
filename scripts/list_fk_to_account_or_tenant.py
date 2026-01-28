# scripts/list_fk_to_account_or_tenant.py
import django
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# setup Django environment if running as standalone
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palmtree_etl.settings")
django.setup()

from django.apps import apps
from django.db.models import ForeignKey
from tenants.models import Account, Tenant  # adjust if in another app

EXCLUDE_FIELDS = [
    ("tenants", "UserAccount", "account"),
    ("contracts", "Customer", "tenant"),
    ("contracts", "Vehicle", "tenant"),
]

def generate_rls_sql():
    rls_items = []

    for model in apps.get_models():
        for field in model._meta.get_fields():
            if isinstance(field, ForeignKey):
                if field.remote_field.model in [Account, Tenant]:
                    if (model._meta.app_label, model.__name__, field.name) in EXCLUDE_FIELDS:
                        continue

                    rls_items.append({
                        "table": model._meta.db_table,
                        "field": field.name,
                        "related_model": field.remote_field.model.__name__
                    })

    # Print SQL for each
    for item in rls_items:
        table = item["table"]
        field = item["field"]
        related = item["related_model"]

        print(f"-- RLS policy for {table}.{field} ({related})")
        print(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        print(f"DROP POLICY IF EXISTS {table}_{field}_rls_policy ON {table};")
        print(f"CREATE POLICY {table}_{field}_rls_policy ON {table}")
        print(f"    USING ({field} = current_setting('app.current_{related.lower()}')::uuid);")
        print()

# ----------------------
# Run
# ----------------------
if __name__ == "__main__":
    generate_rls_sql()


# To disable RLS:

#ALTER TABLE tenants_group DISABLE ROW LEVEL SECURITY;
#ALTER TABLE tenants_tenant DISABLE ROW LEVEL SECURITY;

