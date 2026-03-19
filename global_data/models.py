from django.db import models
from core.models import CoreModel, FixtureControlledModel
from core.models import SHORT_LEN

class Marque(CoreModel, FixtureControlledModel):
    name = models.CharField(max_length=30)
    short = models.CharField(max_length=SHORT_LEN, blank=True) #remove blank=True, 

    def save(self, *args, **kwargs):
        if self.short:
            self.short = self.short.upper()  # enforce uppercase
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
class Brand(CoreModel, FixtureControlledModel):
    marque = models.ForeignKey(Marque, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    short = models.CharField(max_length=SHORT_LEN, blank=True) #remove blank=True, 

    def save(self, *args, **kwargs):
        if self.short:
            self.short = self.short.upper()  # enforce uppercase
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    