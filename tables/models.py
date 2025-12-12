from django.db import models
from django.contrib.auth.models import User
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
    
    # COSTO 1: Solo Ingredientes (Materia Prima)
    @property
    def costo_receta(self):
        total_costo = Decimal('0.00')
        for ingrediente in self.ingredientes.all():
            if ingrediente.insumo:
                total_costo += ingrediente.cantidad * ingrediente.insumo.costo_unitario
        return total_costo

    # COSTO 2: Suma de Costos Adicionales (Mano de obra, gas, etc)
    @property
    def costo_indirectos_total(self):
        total = Decimal('0.00')
        for costo in self.costos_adicionales.all():
            total += costo.monto_calculado
        return total

    # COSTO 3: Costo TOTAL FINAL (Ingredientes + Indirectos)
    @property
    def costo_total_real(self):
        return self.costo_receta + self.costo_indirectos_total

    # GANANCIA REAL (Precio Venta - Costo Total Real)
    @property
    def ganancia_estimada(self):
        return self.precio - self.costo_total_real

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
    
# 1. MAESTRO DE COSTOS ADICIONALES (Configuración Global)
class CostoAdicional(models.Model):
    TIPOS_CALCULO = [
        ('FIJO', 'Monto Fijo ($)'),
        ('PORCENTAJE', '% del Costo de Receta'),
    ]
    
    nombre = models.CharField(max_length=100) # Ej: "Mano de Obra", "Gas", "Empaque"
    tipo = models.CharField(max_length=15, choices=TIPOS_CALCULO, default='FIJO')
    valor_defecto = models.DecimalField(max_digits=10, decimal_places=2, help_text="Ej: 0.50 para $0.50 o 10 para 10%")

    def __str__(self):
        signo = "$" if self.tipo == 'FIJO' else "%"
        return f"{self.nombre} ({self.valor_defecto}{signo})"

# 2. RELACIÓN PRODUCTO <-> COSTO
class CostoAsignadoProducto(models.Model):
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, related_name='costos_adicionales')
    costo_adicional = models.ForeignKey(CostoAdicional, on_delete=models.PROTECT)
    valor_aplicado = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor específico para este producto")

    @property
    def monto_calculado(self):
        """Traduce el porcentaje o fijo a dinero real"""
        if self.costo_adicional.tipo == 'FIJO':
            return self.valor_aplicado
        else:
            # Si es porcentaje, calculamos sobre el costo de los ingredientes
            # (Valor / 100) * CostoReceta
            return (self.valor_aplicado / 100) * self.producto.costo_receta