from django.db import models


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
    