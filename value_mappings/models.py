from django.db import models

class ValueMappingGroup(models.Model):
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    convert_source_to_lowercase_first = models.BooleanField(default=True)

    def __str__(self):
        return self.code
    
class ValueMapping(models.Model):
    """
    Generic value mapping table.
    Each mapping belongs to a group (e.g., 'fuel types') and maps from a source code to a canonical code/value.
    """
    group = models.ForeignKey(ValueMappingGroup, on_delete=models.DO_NOTHING, related_name="mappings",)
    from_code = models.CharField(
        max_length=255,
        help_text="Original/source value/code"
    )
    to_code = models.CharField(
        max_length=255,
        help_text="Normalized/canonical value/code"
    )

    class Meta:
        unique_together = ("group", "from_code")

    def __str__(self):
        return f"{self.group.code}: {self.from_code} → {self.to_code}"
    