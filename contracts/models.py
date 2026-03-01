from django.db import models
from tenants.models import Tenant
from core.models import CoreModel

OPT_IN_TRI_STATE_CHOICES = [
    ('true', 'True'),
    ('false', 'False'),
    ('unspecified', 'Unspecified'),
    ('missing', 'Missing'),          # source data didn’t provide it
]

class Customer(CoreModel):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="customers"
    )

    external_retailer_id = models.CharField(
        max_length=100,
        help_text="Retailer identifier from source system"
    )

    external_customer_id = models.CharField(
        max_length=100,
        help_text="Customer identifier from source system"
    )

    title = models.CharField(
        max_length=20,
        blank=True,
        help_text="e.g. Mr, Mrs, Ms, Dr"
    )

    first_name = models.CharField(
        max_length=100,
        blank=True
    )

    last_name = models.CharField(
        max_length=100,
        blank=True
    )

    salutation = models.CharField(
        max_length=150,
        blank=True,
        help_text="e.g. 'Dear John', 'Dear Mr Smith'"
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    mobile_phone = models.CharField(
        max_length=30,
        blank=True,
        help_text="Mobile phone number"
    )

    home_phone = models.CharField(
        max_length=30,
        blank=True,
        help_text="Home phone number"
    )

    address_line_1 = models.CharField(
        max_length=255,
        blank=True
    )

    address_line_2 = models.CharField(
        max_length=255,
        blank=True
    )

    address_line_3 = models.CharField(
        max_length=255,
        blank=True
    )

    address_line_4 = models.CharField(
        max_length=255,
        blank=True
    )

    address_line_5 = models.CharField(
        max_length=255,
        blank=True
    )

    postcode = models.CharField(
        max_length=20,
        blank=True,
        help_text="Postcode"
    )

    email_opt_in_value = models.CharField(
        max_length=12,
        choices=OPT_IN_TRI_STATE_CHOICES,
        default='missing',
        verbose_name="Tri-state flag",
        help_text="The customer opted in or out of receiving marketing via email: True, False, or Unspecified",
    )

    email_opt_in_date = models.DateField(
        null=True,          # allows database NULL
        blank=True,         # allows empty form input in admin/forms
        verbose_name="Mobile op-in date",
        help_text="The date the customer last opted in or out of receiving marketing via their email"
    )

    home_phone_opt_in_value = models.CharField(
        max_length=12,
        choices=OPT_IN_TRI_STATE_CHOICES,
        default='missing',
        verbose_name="Tri-state flag",
        help_text="The customer opted in or out of receiving marketing via their home phone number: True, False, or Unspecified",
    )

    home_phone_opt_in_date = models.DateField(
        null=True,          # allows database NULL
        blank=True,         # allows empty form input in admin/forms
        verbose_name="Mobile op-in date",
        help_text="The date the customer last opted in or out of receiving marketing via their home phone number"
    )

    mobile_opt_in_value = models.CharField(
        max_length=12,
        choices=OPT_IN_TRI_STATE_CHOICES,
        default='missing',
        verbose_name="Tri-state flag",
        help_text="The customer opted in or out of receiving marketing via their mobile phone number: True, False, or Unspecified",
    )

    mobile_opt_in_date = models.DateField(
        null=True,          # allows database NULL
        blank=True,         # allows empty form input in admin/forms
        verbose_name="Mobile op-in date",
        help_text="The date the customer last opted in or out of receiving marketing via their mobile phone number"
    )

    class Meta:
        db_table = "contract_customer"
        indexes = [
            models.Index(fields=["tenant", "external_customer_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "external_customer_id"],
                name="uniq_customer_per_tenant"
            )
        ]


    def __str__(self):
        return f"{self.external_customer_id} ({self.tenant})"


class Vehicle(CoreModel):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.PROTECT,
        related_name="vehicles"
    )

    external_retailer_id = models.CharField(
        max_length=20,
        help_text="Retailer identifier from source system"
    )

    external_vehicle_id = models.CharField(
        max_length=20,
        help_text="Vehicle unique identifier (number) from source system"
    )

    registration_number = models.CharField(
        max_length=20,
        help_text="Vehicle number from source system"
    )

    registration_date = models.DateField(
        null=True,          # allows database NULL
        blank=True,         # allows empty form input in admin/forms
        verbose_name="Registration date",
        help_text="The date the vehicle was first registered"
    )

    vin = models.CharField(
        max_length=17,
        help_text="VIN from source system"
    )

    brand = models.CharField(
        max_length=20,
        blank=True,
        help_text="e.g. BMW"
    )

    model = models.CharField(
        max_length=20,
        blank=True,
        help_text="e.g. 118d"
    )

    variant = models.CharField(
        max_length=20,
        blank=True,
        help_text="e.g. 1D31A8"
    )

    fuel_type = models.CharField(
        max_length=20,
        blank=True,
        help_text="e.g. DIESEL"
    )

    class Meta:
        db_table = "contract_vehicle"
        indexes = [
            models.Index(fields=["tenant", "external_vehicle_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "external_vehicle_id"],
                name="uniq_vehicle_per_tenant"
            )
        ]

    def __str__(self):
        return f"{self.external_retailer_id} / {self.external_vehicle_id} / {self.registration_number} / {self.vin}"

