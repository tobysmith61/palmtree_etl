from django.db import models
from core.models import TimeStampedModel, Address
import uuid
from django.conf import settings
from canonical.models import Job

class Marque(models.Model):
    name = models.CharField(max_length=30)
    short = models.CharField(max_length=8, blank=True) #remove blank=True, 

    def save(self, *args, **kwargs):
        if self.short:
            self.short = self.short.upper()  # enforce uppercase
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Brand(models.Model):
    marque = models.ForeignKey(Marque, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    short = models.CharField(max_length=8, blank=True) #remove blank=True, 

    def save(self, *args, **kwargs):
        if self.short:
            self.short = self.short.upper()  # enforce uppercase
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Account(models.Model):
    name = models.CharField(max_length=255)
    short = models.CharField(max_length=8, blank=True) #remove blank=True, 

    def save(self, *args, **kwargs):
        if self.short:
            self.short = self.short.upper()  # enforce uppercase
        super().save(*args, **kwargs)

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

class Location(Address):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    short = models.CharField(
        max_length=8,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"

    def __str__(self):
        return self.short + ' / ' + self.postcode

class Tenant(TimeStampedModel):
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.CASCADE) #remove blank=True, null=True
    rls_key = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="RLS Key",
    )
    internal_tenant_code = models.CharField(
        max_length=26,
        unique=True,
        blank=True,
        verbose_name='Internal tenant code',
        help_text='Internal (to palmTree) tenant code made up of ACCOUNT/LOCATION/BRAND. Leave blank and I\'ll default for you'
    )
    external_tenant_code = models.CharField(max_length=100)
    desc = models.CharField(max_length=200)
    logo_path = models.CharField(max_length=255, blank=True)
    is_live = models.BooleanField(default=False)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.DO_NOTHING)#if the parent goes, the child goes too
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.DO_NOTHING)

    def __str__(self):
        return self.desc

    def save(self, *args, **kwargs):
        if not self.internal_tenant_code:  # only set if not already provided
            self.internal_tenant_code = f"{self.account.short}/{self.location.short}/{self.brand.short}"
        super().save(*args, **kwargs)

class UserAccount(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "account")

    def __str__(self):
        return f"{self.user} → {self.account}"

class TenantMapping(models.Model):
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="tenant_mappings"
    )
    source_system_field_value = models.CharField(max_length=255)
    mapped_tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="tenant_mappings"
    )
    effective_from_date = models.DateField(
        help_text="The date the mapping is valid from"
    )

    class Meta:
        unique_together = ('account', 'source_system_field_value', 'effective_from_date')
        verbose_name = "Tenant Code Mapping"
        verbose_name_plural = "Tenant Code Mappings"

# tenant_internal-code should be account(short)_tenant(short) e.g. STELLANT_GODL_FIAT
# need function to build internal tenant_code
# choices are ACCOUNT, LOCATION, BRAND, all upper case ALPHA only

class AccountJob(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.job}"
