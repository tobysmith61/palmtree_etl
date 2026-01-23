from django.db import models
from core.models import TimeStampedModel
import uuid
from django.conf import settings

class Tenant(TimeStampedModel):
    rls_key = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="RLS Key",
    )
    internal_tenant_code = models.CharField(
        max_length=50,
        verbose_name='Internal (to palmTree) tenant code'
    )
    external_tenant_code = models.CharField(max_length=100)
    desc = models.CharField(max_length=200)

    def __str__(self):
        return self.internal_tenant_code

class UserTenant(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "tenant")

    def __str__(self):
        return f"{self.user} → {self.tenant}"
    