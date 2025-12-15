from django.db import models
from django.contrib.auth.models import User
from inventory.models import Insumo
from decimal import Decimal

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
    OPCIONES_TAMANO = [
        ('IND', 'Individual'),
        ('MED', 'Mediana'),
        ('FAM', 'Familiar'),
        ('UNI', 'Único/Bebida'),
    ]

    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Venta ($)")
    tamano = models.CharField(max_length=3, choices=OPCIONES_TAMANO, default='UNI')
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos')
    
    # OPCIONAL: Imagen del producto
    # imagen = models.ImageField(upload_to='productos/', blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} ({self.tamano})"

    # --- LÓGICA DE COSTOS AUTOMÁTICA ---
    @property
    def costo_receta(self):
        """Calcula cuánto cuesta hacer este producto sumando sus ingredientes"""
        total_costo = Decimal('0.00')
        # Recorremos todos los ingredientes de este producto
        for ingrediente in self.ingredientes.all():
            if ingrediente.insumo:
                # Costo = Cantidad de la receta * Costo Promedio actual del insumo
                costo_insumo = ingrediente.cantidad * ingrediente.insumo.costo_unitario
                total_costo += costo_insumo
        return total_costo

    @property
    def ganancia_estimada(self):
        """Muestra cuánto ganas: Precio Venta - Costo Receta"""
        return self.precio - self.costo_receta
    
    @property
    def margen_ganancia(self):
        """Margen en porcentaje"""
        if self.precio > 0:
            return (self.ganancia_estimada / self.precio) * 100
        return 0

# Tu modelo original de Mesas
class Table(models.Model):
    number = models.PositiveIntegerField(unique=True, verbose_name="Número de Mesa")
    is_occupied = models.BooleanField(default=False, verbose_name="¿Ocupada?")

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f"{self.nombre} ({self.tamano})"

    # --- LÓGICA DE COSTOS AUTOMÁTICA ---
    @property
    def costo_receta(self):
        """Calcula cuánto cuesta hacer este producto sumando sus ingredientes"""
        total_costo = Decimal('0.00')
        # Recorremos todos los ingredientes de este producto
        for ingrediente in self.ingredientes.all():
            if ingrediente.insumo:
                # Costo = Cantidad de la receta * Costo Promedio actual del insumo
                costo_insumo = ingrediente.cantidad * ingrediente.insumo.costo_unitario
                total_costo += costo_insumo
        return total_costo

    @property
    def ganancia_estimada(self):
        """Muestra cuánto ganas: Precio Venta - Costo Receta"""
        return self.precio - self.costo_receta
    
    @property
    def margen_ganancia(self):
        """Margen en porcentaje"""
        if self.precio > 0:
            return (self.ganancia_estimada / self.precio) * 100
        return 0

    
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
    
# --- NUEVO MODELO: LA RECETA ---
class IngredienteProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='ingredientes')
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, verbose_name="Insumo (Inventario)")
    cantidad = models.DecimalField(max_digits=10, decimal_places=4, help_text="Cantidad a descontar del inventario (Ej: 0.200 para 200g)")

    def __str__(self):
        return f"{self.insumo.nombre} ({self.cantidad} {self.insumo.unidad.codigo})"

    # Calculamos el costo parcial solo para mostrarlo en el admin
    @property
    def costo_parcial(self):
        return self.cantidad * self.insumo.costo_unitario