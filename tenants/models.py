from django.db import models
from core.models import TimeStampedModel
import uuid
from django.conf import settings
from mptt.models import MPTTModel, TreeForeignKey

class Account(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

# For various collections of Tenants
class TenantGroupType(models.TextChoices):
    ACCOUNT = "billing", "Account / Billing Group" # Account details is at Group root node
    DATAFEED = "data-feed", "Data Feed Group (e.g. for multi-tenant data feed). Provides sFTP drop folder" # e.g. a multi-fran multi-location DMS instance suppling 1 data feed for N tenants

    OPERATING = "operating", "Operating Group (e.g. a Dealer Group)" # Could be single group or a group of groups
    REGIONAL = "regional", "Regional Group (e.g. for NSC)" # e.g. Could be 200 sites for a brand nationally, split into 8 regions
    ROOFTOP = "rooftop", "Multiple brands at a single physical location" # e.g. could be Group1 Hindhead who sell BMW and Mini, or Stellantis Godalming who sell 8 brands

    CALLCENTRE = "call-centre", "Call Centre (e.g. some brands for the rooftop or multi location)"

    @property
    def icon(self):
        return {
            self.ACCOUNT: "💰", # Top level account (for subscription billing)
            self.DATAFEED: "🖥️", # Not bound to account. Allows supply of sFTP drop location.
                                 # Need to map retailer code in feed to tenants for RLS.

            self.OPERATING: "🏢", # These types are for reporting and analytics
            self.REGIONAL: "🌍",
            self.ROOFTOP: "🏠",

            self.CALLCENTRE: "📞", # Special case for where Tenants cross multiple accounts
        }[self]
    
    # Need to apply visibility of configured groups to Users who are tied to email domain.
    # Users need palmTree roles
    # Roles have privileges

    # Add RLS policies via Meta on Models
    # Any Table with Tenant field

    # Roles
    # =====
    # IT support

    # Maintain Marques (e.g. Volkswagen = Audit, SEAT and VW etc, similar for Stellantis)

class Group(MPTTModel):
    name = models.CharField(max_length=255)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    group_type = models.CharField(
        max_length=20,
        choices=TenantGroupType.choices,
        blank=True,
        help_text="Categorise the type of group"
    )

    class MPTTMeta:
        order_insertion_by = ['name']

    def __str__(self):
        return self.name

class Tenant(TimeStampedModel):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
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
    logo_path = models.CharField(max_length=255, blank=True)
    group = models.ForeignKey(Group, null=True, blank=True, on_delete=models.DO_NOTHING)
    live = models.BooleanField(default=False)

    def __str__(self):
        return self.internal_tenant_code + ' / ' + self.desc

class UserAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "account")

    def __str__(self):
        return f"{self.user} → {self.account}"

