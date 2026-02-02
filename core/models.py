from django.db import models

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Address(models.Model):
    address_line_1 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    address_line_3 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    address_line_4 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    address_line_5 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    postcode = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "UK Address"
        verbose_name_plural = "UK Addresses"
        abstract = True

    def __str__(self):
        return ", ".join(
            filter(
                None,
                [
                    self.address_line_1,
                    self.address_line_2,
                    self.address_line_3,
                    self.address_line_4,
                    self.address_line_5,
                    self.postcode,
                ],
            )
        )