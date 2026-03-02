# file_ingestion/models.py
from django.db import models
from core.models import CoreModel

class IngestedFile(CoreModel):
    filename = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("processed", "Processed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    def __str__(self):
        return self.filename
