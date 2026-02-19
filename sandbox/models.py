from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from tenants.models import Account, Tenant
from django.core.exceptions import ValidationError

# For various collections of Tenants
class TenantGroupType(models.TextChoices):
    ACCOUNT = "billing", "Account / Billing Group"
    DATAFEED = "data-feed", "Data Feed Group (e.g. for multi-tenant data feed)"
    OPERATING = "operating", "Operating Group (e.g. a Dealer Group)"
    REGIONAL = "regional", "Regional Group (e.g. for NSC)"
    ROOFTOP = "rooftop", "Multiple brands at a single physical location"
    CALLCENTRE = "call-centre", "Call Centre (e.g. some brands for the rooftop or multi location)"

    @property
    def icon(self):
        return {
            self.ACCOUNT: "💰",
            self.DATAFEED: "🖥️",
            self.OPERATING: "🏢",
            self.REGIONAL: "🌍",
            self.ROOFTOP: "🏠",
            self.CALLCENTRE: "📞",
        }[self]

    @property
    def requires_all_tenants(self) -> bool:
        return self in {
            self.OPERATING, self.REGIONAL
        }

    @property
    def one_per_account(self) -> bool:
        return self in {
            self.ACCOUNT, self.OPERATING
        }
    
class TenantGroup(MPTTModel):
    NODE_TYPE_CHOICES = [
        ("root", "Root"),
        ("group", "Group"),
        ("tenant", "Tenant"),
    ]

    group_label = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="children",
    )
    node_type = models.CharField(
        max_length=10,
        choices=NODE_TYPE_CHOICES,
        default="group",
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="tenant_group_roots"
    )
    root_label = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Label for the tree root. Only used for root nodes."
    )
    group_type = models.CharField(
        max_length=20,
        choices=TenantGroupType.choices,
        default=TenantGroupType.OPERATING,
        help_text="Type of this group"
    )
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="group_nodes",
        help_text="If set, this node represents a tenant (leaf node).",
    )

    ftp_drop_folder_path = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Path of sFTP drop folder from this platform"
    )

    class MPTTMeta:
        order_insertion_by = ["group_label"]

    def __str__(self):
        if self.node_type == "root" and self.root_label:
            return f"🌳 {self.root_label}"
        if self.node_type == "group" and self.group_label:
            return f"🏢 {self.group_label}"
        if self.node_type == "tenant" and self.tenant:
            return f"🌿 {self.tenant}"
        # Fallback to group_label or PK if nothing else
        return f"<TenantGroup {self.pk}>"

    def clean(self):
        """
        Validates that the fields correspond to the node_type:
        - root: must have root_label, no group_label, no tenant
        - group: must have group_label, no root_label, no tenant
        - tenant: must have tenant, no root_label, no group_label
        """
        if self.node_type == "root":
            if not self.root_label:
                raise ValidationError("Root nodes must have a root_label.")
            if self.group_label or self.tenant:
                raise ValidationError("Root nodes cannot have group_label or tenant set.")
        elif self.node_type == "group":
            if not self.group_label:
                raise ValidationError("Group nodes must have a group_label.")
            if self.root_label or self.tenant:
                raise ValidationError("Group nodes cannot have root_label or tenant set.")
        elif self.node_type == "tenant":
            if not self.tenant:
                raise ValidationError("Tenant nodes must have a tenant assigned.")
            if self.root_label or self.group_label:
                raise ValidationError("Tenant nodes cannot have root_label or group_label set.")
        else:
            raise ValidationError(f"Unknown node_type: {self.node_type}")
        
        # ---- Group type validation ----
        if self.group_type == TenantGroupType.DATAFEED:
            # assuming you have an ftp_path field
            if not getattr(self, "ftp_drop_folder_path", None):
                raise ValidationError("Data Feed groups must have an ftp_drop_folder_path specified.")
            