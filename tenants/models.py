from django.db import models
from core.models import TimeStampedModel, Address
import uuid
from django.conf import settings
from canonical.models import Job, TableData
from django.utils.timezone import now
from django.core.exceptions import ValidationError

import os
import random
import string
from django.contrib import messages

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

class AccountEncryption(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)

    encrypted_dek = models.BinaryField()
    dek_kms_key_id = models.CharField(max_length=255)
    dek_algorithm = models.CharField(
        max_length=50,
        default="AES-256-GCM"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    
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
    account = models.ForeignKey(Account, null=True, blank=True, on_delete=models.CASCADE)
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
        on_delete=models.PROTECT,
    )
    desc = models.CharField(max_length=200)

    def __str__(self):
        return self.desc

    def resolve_tenant(self, source_value, as_of_date=None):
        as_of_date = as_of_date or now().date()

        mapping = (
            self.mapping_codes
            .filter(
                source_system_field_value=source_value,
                effective_from_date__lte=as_of_date,
            )
            .order_by("-effective_from_date")
            .first()
#            .mapped_tenant
#            .internal_tenant_code
        )

        return mapping.mapped_tenant.internal_tenant_code if mapping else None
    
class TenantMappingCode(models.Model):
    tenant_mapping = models.ForeignKey(
        TenantMapping,
        on_delete=models.CASCADE,
        related_name="mapping_codes"
    )
    source_system_field_value = models.CharField(max_length=255)
    mapped_tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="mapping_codes_mapped_to_this_tenant"
    )
    effective_from_date = models.DateField(
        help_text="The date the mapping is valid from"
    )

    class Meta:
        unique_together = ('tenant_mapping', 'source_system_field_value', 'effective_from_date')
        verbose_name = "Tenant mapping code"
        verbose_name_plural = "Tenant mapping codes"

class SFTPDropZone(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    zone_folder = models.CharField(max_length=50)  # e.g. DMS001
    desc = models.CharField(max_length=200)
    scope = models.TextField(max_length=1000)
    sftp_user = models.CharField(max_length=50, editable=False)
    folder_path = models.CharField(max_length=200, editable=False)

    _plaintext_password = None

    def save(self, *args, **kwargs):
        self.full_clean()
        is_new = self._state.adding

        if is_new:
            if not self.zone_folder.strip():
                raise ValidationError("Folder path cannot be empty.")

            # Generate Linux commands
            self.folder_path = f"/srv/sftp/{self.account.short.lower()}/{self.zone_folder}/drop"
            create_folder_command = f"sudo mkdir -p {self.folder_path}"
            ownership_command = f"sudo chown -R ubuntu:ubuntu /srv/sftp/{self.account.short.lower()}/{self.zone_folder}"
            permissions_command = f"sudo chmod -R 750 /srv/sftp/{self.account.short.lower()}/{self.zone_folder}"

            # Store SFTP credentials
            self.sftp_user = f"{self.account.short}_{self.zone_folder}".lower()
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            self._plaintext_password = password

            # Store the commands for display
            self._linux_commands = [create_folder_command, ownership_command, permissions_command]

        super().save(*args, **kwargs)
        
class SFTPDropZoneScopedTenant(models.Model):
    sftp_drop_zone = models.ForeignKey(SFTPDropZone, on_delete=models.CASCADE)
    scoped_tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="scoped_tenants"
    )
    
class AccountTableData(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    table_data_copied_from = models.OneToOneField(
        TableData,
        on_delete=models.PROTECT,
        related_name="account_table_data",
        null=True,
        blank=True,
    )
    data = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of rows, first row is header"
    )

    def __str__(self):
        return self.name
    
    @property
    def data_preview(self):
        # Returns the same data for read-only preview
        return self.data
    
    class Meta:
        verbose_name = "Account table data"
        verbose_name_plural = "Account table data"

class AccountJob(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    sftp_drop_zone = models.ForeignKey(SFTPDropZone, on_delete=models.PROTECT, null=True, blank=True, verbose_name="sFTP drop zone")
    tenant_mapping = models.ForeignKey(TenantMapping, on_delete=models.PROTECT, null=True, blank=True)
    account_table_data = models.ForeignKey(AccountTableData, on_delete=models.PROTECT, null=True, blank=True)
    
    def __str__(self):
        return f"{self.job}"

class Role(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
