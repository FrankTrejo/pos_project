from django.db import models
from django.contrib.auth.models import User

# 1. Modelo para optimizar el BCV (Punto 1)
class TasaBCV(models.Model):
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio en Bs")
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Tasa: {self.precio} (Actualizada: {self.fecha_actualizacion.strftime('%d/%m %H:%M')})"

# 2. Modelos para el POS (Punto 2)
class Categoria(models.Model):
    nombre = models.CharField(max_length=50) # Ej: IND, MED, FAM, BEBIDAS

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    # Opciones fijas para evitar errores de escritura
    OPCIONES_TAMANO = [
        ('IND', 'Individual'),
        ('MED', 'Mediana'),
        ('FAM', 'Familiar'),
        ('UNI', 'Único/Bebida'), # Para cosas que no tienen tamaño (ej: Coca Cola)
    ]

    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    # Agregamos el campo tamano
    tamano = models.CharField(
        max_length=3, 
        choices=OPCIONES_TAMANO, 
        default='UNI',
        verbose_name="Tamaño"
    )
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos')
    
    def __str__(self):
        # Muestra "Pizza (FAM)" o "Coca Cola (UNI)"
        return f"{self.nombre} ({self.tamano}) - ${self.precio}"

# Tu modelo original de Mesas
class Table(models.Model):
    number = models.PositiveIntegerField(unique=True, verbose_name="Número de Mesa")
    is_occupied = models.BooleanField(default=False, verbose_name="¿Ocupada?")

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f"Mesa {self.number}"
    
class Table(models.Model):
    number = models.PositiveIntegerField(unique=True, verbose_name="Número de Mesa")
    is_occupied = models.BooleanField(default=False, verbose_name="¿Ocupada?")
    
    # --- NUEVO CAMPO ---
    # Relacionamos la mesa con un usuario. 
    # null=True permite que la mesa no tenga mesero (cuando está libre)
    mesero = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='mesas_asignadas')

    class Meta:
        ordering = ['number']

    def __str__(self):
        mesero_nombre = self.mesero.username if self.mesero else "Sin mesero"
        return f"Mesa {self.number} - {mesero_nombre}"