
from django.db import models
from django.contrib.auth.models import User

class UnidadMedida(models.Model):
    nombre = models.CharField(max_length=50, verbose_name="Nombre") # Ej: Kilogramo, Litro, Unidad
    codigo = models.CharField(max_length=10, verbose_name="Abreviatura") # Ej: kg, l, und

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

class CategoriaInsumo(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Insumo(models.Model):
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaInsumo, on_delete=models.SET_NULL, null=True)
    unidad = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT)
    
    # DATOS FINANCIEROS Y DE STOCK
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo ($)")
    stock_actual = models.DecimalField(max_digits=10, decimal_places=3, default=0) # 3 decimales por si usas 0.500 kg
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=3, default=5, verbose_name="Stock Mínimo (Alerta)")
    
    # Para saber si es materia prima o producto directo
    es_materia_prima = models.BooleanField(default=True, help_text="Marcar si se usa para cocinar (Harina). Desmarcar si es reventa (Refresco).")

    def __str__(self):
        return f"{self.nombre} - Stock: {self.stock_actual} {self.unidad.codigo}"
    
    # AGREGA ESTO: Propiedad calculada para ver el total invertido
    @property
    def valor_total_invertido(self):
        # Multiplica Kilos * PrecioUnitario
        return self.stock_actual * self.costo_unitario

class MovimientoInventario(models.Model):
    TIPOS_MOVIMIENTO = [
        ('ENTRADA', 'Compra / Entrada'),
        ('SALIDA', 'Consumo / Merma'),
        ('AJUSTE', 'Ajuste de Inventario'),
    ]

    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=TIPOS_MOVIMIENTO)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    
    # Guardamos el costo en el momento del movimiento (histórico de precios)
    costo_unitario_movimiento = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Costo Unitario ($)")
    
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    nota = models.CharField(max_length=255, blank=True, null=True, help_text="Ej: Compra en mercado, se cayó el frasco, etc.")

    def save(self, *args, **kwargs):
        # LÓGICA DE COSTO PROMEDIO PONDERADO
        if not self.pk: # Solo al crear nuevo registro
            
            if self.tipo == 'ENTRADA':
                # 1. Calcular cuánto valía el inventario ANTES de esta compra
                valor_total_actual = self.insumo.stock_actual * self.insumo.costo_unitario
                
                # 2. Calcular cuánto vale lo que ESTOY COMPRANDO ahora
                valor_total_compra = self.cantidad * self.costo_unitario_movimiento
                
                # 3. Sumar ambos valores
                nuevo_valor_total = valor_total_actual + valor_total_compra
                
                # 4. Sumar el stock físico
                nuevo_stock_total = self.insumo.stock_actual + self.cantidad
                
                # 5. ACTUALIZAR STOCK
                self.insumo.stock_actual = nuevo_stock_total
                
                # 6. CALCULAR EL NUEVO COSTO PROMEDIO (El dato clave para tus recetas)
                # Evitamos división por cero
                if nuevo_stock_total > 0:
                    self.insumo.costo_unitario = nuevo_valor_total / nuevo_stock_total
                
            elif self.tipo in ['SALIDA', 'AJUSTE']:
                # En salida, el costo unitario no cambia, solo baja la cantidad
                self.insumo.stock_actual -= self.cantidad
            
            # Guardamos los cambios en el Insumo padre
            self.insumo.save()
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo} - {self.insumo.nombre} ({self.cantidad})"