from django.db import models
from tenants.models import Account
# Create your models here.

# class Job(models.Model):
#     name = models.CharField(
#         max_length=255,
#         blank=True
#     )
#     account = models.ForeignKey(
#         Account,
#         on_delete=models.CASCADE,
#         related_name="tenant_group_roots"
#     )
#     tenant_mapping_schema   # from source data (DMS extract - Customer) company field (e.g. 'Godalming Fiat') to
#                             # STELLANT/GODAFIAT/
#                             # ACCOUNT /TENANT  /
#     #tenant mapping is not data transformation
#     #tenant mapping to be controlled by Superuser only, readonly by Account admin
#     source_data_contract = 
#     test_data = 
#     source_mappings = 
#     canonical_contract = 


#     def __str__(self):
#         return self.name
