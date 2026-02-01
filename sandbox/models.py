from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from tenants.models import Account

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
        ("group", "Group"),
        ("tenant", "Tenant"),
    ]

    name = models.CharField(max_length=100)
    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
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
    tree_label = models.CharField(
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

    class MPTTMeta:
        order_insertion_by = ["name"]

    def __str__(self):
        if self.is_root_node() and self.tree_label:
            return f"{self.tree_label} ({self.get_node_type_display()})"
        # ← this line makes tenants look different
        return f"🌿 {self.name}" if self.node_type == "tenant" else self.name