from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal

# 1. UNIDAD DE MEDIDA
class UnidadMedida(models.Model):
    nombre = models.CharField(max_length=50)
    codigo = models.CharField(max_length=10)
    factor = models.DecimalField(max_digits=10, decimal_places=4, default=1, help_text="1 para Gramos/ML. 1000 para KG/L.")

    def __str__(self): return f"{self.nombre} ({self.codigo})"

class CategoriaInsumo(models.Model):
    nombre = models.CharField(max_length=100)
    def __str__(self): return self.nombre

class Insumo(models.Model):
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaInsumo, on_delete=models.SET_NULL, null=True)
    unidad = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT, verbose_name="Unidad Base")

    # MAESTRO DE COSTOS
    cantidad_por_precio = models.DecimalField(max_digits=10, decimal_places=2, default=1000, verbose_name="Cant. Ref")
    precio_mercado = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Precio Mercado ($)")
    merma_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="% Merma")
    
    # COSTO Y STOCK
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=6, default=0, verbose_name="Costo Real x Gramo")
    stock_actual = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=500)
    es_insumo_compuesto = models.BooleanField(default=False)

    def __str__(self): return f"{self.nombre}"
    
    # PROPIEDAD PARA REPORTES
    @property
    def valor_total_invertido(self):
        return round(self.stock_actual * self.costo_unitario, 2)


    # 1. MÉTODO DE CÁLCULO MEJORADO (Usa .update para evitar bucles)
    def calcular_costo_desde_subreceta(self):
        if not self.es_insumo_compuesto:
            return

        total_costo = Decimal('0.0')
        total_peso = Decimal('0.0')
        
        # Sumamos ingredientes
        for componente in self.componentes.all():
            total_costo += componente.cantidad * componente.insumo_hijo.costo_unitario
            total_peso += componente.cantidad
            
        # LÓGICA DE CATEGORÍA
        nombre_cat = self.categoria.nombre.upper() if self.categoria else ""
        ES_MEZCLA = nombre_cat in ['INSUMO PRODUCIDO', 'SUB-RECETA', 'MEZCLA', 'MASAS']

        if ES_MEZCLA and total_peso > 0:
            # Caso MASA: Dividimos (1.63 / 1549 = 0.00105)
            nuevo_costo = total_costo / total_peso
        else:
            # Caso PIZZA: Sumamos directo (1.63)
            nuevo_costo = total_costo

        # Actualizamos DIRECTO en la base de datos para no llamar a save() de nuevo
        Insumo.objects.filter(pk=self.pk).update(costo_unitario=nuevo_costo)

    # 2. MÉTODO SAVE QUE DISPARA EL CÁLCULO
    def save(self, *args, **kwargs):
        # A) Lógica para Materia Prima (Precio Mercado)
        if not self.es_insumo_compuesto and self.precio_mercado >= 0:
            cantidad_ref = self.cantidad_por_precio if self.cantidad_por_precio > 0 else 1
            rendimiento = 1 - (self.merma_porcentaje / 100)
            precio_base = self.precio_mercado / cantidad_ref
            
            if rendimiento > 0:
                self.costo_unitario = precio_base / rendimiento
            else:
                self.costo_unitario = precio_base

        # B) Guardamos los cambios básicos (Nombre, Categoría, etc)
        super().save(*args, **kwargs)

        # C) SI ES COMPUESTO -> FORZAMOS RE-CÁLCULO INMEDIATAMENTE
        # Esto arregla tu problema: al cambiar categoría y guardar, se recalcula el precio.
        if self.es_insumo_compuesto:
            self.calcular_costo_desde_subreceta()

class IngredienteCompuesto(models.Model):
    insumo_padre = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='componentes')
    insumo_hijo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name='usado_en_compuestos')
    cantidad = models.DecimalField(max_digits=10, decimal_places=4, help_text="Cantidad necesaria para fabricar 1 unidad del padre")

class MovimientoInventario(models.Model):
    TIPOS_MOVIMIENTO = [('ENTRADA', 'Compra/Prod'), ('SALIDA', 'Consumo/Merma'), ('AJUSTE', 'Ajuste')]
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=TIPOS_MOVIMIENTO)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    unidad_movimiento = models.ForeignKey(UnidadMedida, on_delete=models.SET_NULL, null=True)
    costo_unitario_movimiento = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    nota = models.CharField(max_length=255, blank=True, null=True)

# SEÑAL (Mantén la que tenías para actualizar stock, solo asegúrate que funcione)
@receiver(post_save, sender=MovimientoInventario)
def actualizar_stock_conversion(sender, instance, created, **kwargs):
    if created:
        insumo = instance.insumo
        factor = instance.unidad_movimiento.factor if instance.unidad_movimiento else 1
        cantidad_en_gramos = instance.cantidad * factor
        
        # Actualizar Stock
        if instance.tipo == 'ENTRADA' or instance.tipo == 'AJUSTE':
            insumo.stock_actual += cantidad_en_gramos
            # Si es compra directa, actualizamos costo (solo si no es compuesto)
            costo_nuevo = instance.costo_unitario_movimiento / factor if (factor > 0 and instance.costo_unitario_movimiento > 0) else 0
            if not insumo.es_insumo_compuesto and costo_nuevo > 0 and instance.tipo == 'ENTRADA':
                 insumo.costo_unitario = costo_nuevo
                 
        elif instance.tipo == 'SALIDA':
            insumo.stock_actual -= cantidad_en_gramos
            if insumo.stock_actual < 0: insumo.stock_actual = 0
            
        insumo.save()