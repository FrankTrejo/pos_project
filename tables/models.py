from django.db import models

# Create your models here.
# tables/models.py
from django.db import models

class Table(models.Model):
    number = models.PositiveIntegerField(unique=True, verbose_name="Número de Mesa")
    is_occupied = models.BooleanField(default=False, verbose_name="¿Ocupada?")

    class Meta:
        ordering = ['number'] # Siempre mostrar en orden numérico

    def __str__(self):
        return f"Mesa {self.number}"