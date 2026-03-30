from django.db import models

import math

NONCE_LEN = 12
SHORT_LEN = 8

def encr_b64_size(plaintext_len, nonce_len=NONCE_LEN, tag_len=SHORT_LEN):
    """
    Estimate the number of characters needed to store an AES-GCM encrypted value
    in Base64.
    
    :param plaintext_len: length of the plaintext in bytes
    :param nonce_len: length of AES-GCM nonce in bytes (default 12)
    :param tag_len: length of AES-GCM authentication tag in bytes (default 16)
    :return: approximate number of Base64 characters
    """
    total_bytes = plaintext_len + nonce_len + tag_len
    # Base64 increases size by 4/3, round up to nearest whole character
    num_base64_chars = math.ceil(total_bytes * 4 / 3)
    return num_base64_chars + 4

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class SoftDeleteModel(models.Model):
    deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

class CoreModel(TimeStampedModel, SoftDeleteModel):
    class Meta:
        abstract = True

class FixtureControlledModel(models.Model):
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
    

class CoreContractModel(TimeStampedModel, models.Model):
    row_hash = models.CharField(max_length=64)

    class Meta:
        abstract = True
