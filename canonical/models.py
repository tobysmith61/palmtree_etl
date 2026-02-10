from django.db import models
from value_mappings.models import ValueMappingGroup
from django.core.exceptions import ValidationError


class CanonicalSchema(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    contract = models.CharField(max_length=100, blank=True)
    requires_tenant_mapping = models.BooleanField(default=False)

    def __str__(self):
        return self.name
    
class SourceSchema(models.Model):
    name = models.CharField(max_length=50)
    system = models.CharField(max_length=50)  # e.g. "CDK", "Pinewood"
    
    def __str__(self):
        return f"{self.system} - {self.name}"

class FieldMapping(models.Model): # rename as it not longer maps! it is just a list of fields
    source_schema = models.ForeignKey(SourceSchema, on_delete=models.CASCADE, related_name="field_mappings")
    source_field_name = models.CharField(max_length=100, null=True, blank=True)
    order = models.PositiveIntegerField()
    active = models.BooleanField(default=True)
    is_tenant_mapping_source = models.BooleanField(default=False)

    # 🔐 Governance / compliance
    is_pii = models.BooleanField(default=False)
    requires_encryption = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.source_field_name}"

    @property
    def is_new(self):
        return not self.source_field_name

    @property
    def is_removed_from_canonical(self):
        if not self.source_schema or not self.source_schema.canonical_schema:
            return False

        return not self.source_schema.canonical_schema.fields.filter(
            id=self.canonical_field_id
        ).exists()


class CanonicalField(models.Model):
    FORMAT_NONE = "none"
    FORMAT_EMAIL = "email"
    FORMAT_POSTCODE_UK = "postcode_uk"

    FORMAT_TYPE_CHOICES = [
        (FORMAT_NONE, "None"),
        (FORMAT_EMAIL, "Email"),
        (FORMAT_POSTCODE_UK, "UK Postcode"),
    ]

    DATA_TYPE_CHOICES = [
        ("string", "String"),
        ("integer", "Integer"),
        ("date", "Date"),
        ("boolean", "Boolean"),
        ("email", "Email"),
        ("mapped_string", "Mapped string"),
        ("tenant_mapping", "Tenant code mapping"),
    ]

    schema = models.ForeignKey(CanonicalSchema, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=100)
    source_field = models.ForeignKey(FieldMapping, on_delete=models.CASCADE, related_name="field_mappings", null=True, blank=True)
    data_type = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES
    )

    # 🔹 Generic, composable rules
    normalisation = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Normalisation rules",
    )

    # 🔹 Semantic format (one per field)
    format_type = models.CharField(
        max_length=30,
        choices=FORMAT_TYPE_CHOICES,
        default=FORMAT_NONE,
        help_text="Semantic format (e.g. email, UK postcode)"
    )

    # 🔢 Ordering / constraints
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField()

    value_mapping_group = models.ForeignKey(
        ValueMappingGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Optional value mapping (e.g. fuel types)"
    )

    class Meta:
        unique_together = ("schema", "name")
        ordering = ["order"]

    def __str__(self):
        return f"{self.schema.name}.{self.name}"

    def clean(self):
        """
        Validate that value_mapping_group is only used for mapped strings.
        """
        if self.data_type == "mapped_string" and not self.value_mapping_group:
            raise ValidationError({
                "value_mapping_group": "Mapped string fields must have a value mapping group."
            })

        if self.data_type != "mapped_string" and self.value_mapping_group:
            raise ValidationError({
                "value_mapping_group": "Only mapped string fields can have a value mapping group."
            })
  
class TableData(models.Model):
    name = models.CharField(max_length=100)
    source_schema = models.OneToOneField(
        SourceSchema,
        on_delete=models.PROTECT,
        related_name="table_data",
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
        verbose_name = "Table data"
        verbose_name_plural = "Table data"


class Job(models.Model):
    desc = models.CharField(max_length=100)
    canonical_schema = models.ForeignKey(CanonicalSchema, on_delete=models.CASCADE)
    source_schema = models.ForeignKey(SourceSchema, on_delete=models.CASCADE)
    test_table = models.ForeignKey(
        TableData, 
        on_delete=models.CASCADE, 
        verbose_name="Test transformation with:"
    )
    one_or_many_source_files = models.BooleanField(default=False)
    source_filename_pattern = models.CharField(
        max_length=50,
    )

    def __str__(self):
        return self.desc
    