from django.db import models
from tenants.models import Tenant

class BaseRawData(models.Model):
    source_name = models.CharField(max_length=255)
    source_file = models.CharField(max_length=512, null=True, blank=True)
    source_row_number = models.IntegerField(null=True, blank=True)
    row_hash = models.CharField(max_length=64)
    business_key_hash = models.CharField(max_length=64, null=True, blank=True)
    payload = models.JSONField()
    ingested_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    is_current = models.BooleanField(default=False)
    last_seen_run_id = models.CharField(max_length=19, db_index=True)
    is_deleted_at_source = models.BooleanField(default=False)
    
    class Meta:
        abstract = True

class RawCustomerVehicleData(BaseRawData):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="raw_customer_vehicle_data"
    )

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "business_key_hash", "is_current"]),
        ]

    def __str__(self):
        return f"{self.tenant} - source row {self.source_row_number}"
    

class RawRecallData(BaseRawData):
    class Meta:
        indexes = [
            models.Index(fields=["business_key_hash", "is_current"]),
        ]

    def __str__(self):
        return f"Source row {self.source_row_number}"
    