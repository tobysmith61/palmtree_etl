from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("sandbox", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE sandbox_tenantgroup DROP COLUMN IF EXISTS tenant_tree_id;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
