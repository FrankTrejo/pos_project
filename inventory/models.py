from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# 1. UNIDAD DE MEDIDA CON FACTOR DE CONVERSIÓN
class UnidadMedida(models.Model):
    nombre = models.CharField(max_length=50) # Ej: Gramo, Kilogramo, Litro
    codigo = models.CharField(max_length=10) # Ej: g, kg, l
    
    # NUEVO CAMPO: Factor respecto a la unidad base (Gramo/ML)
    # Gramo = 1
    # Kilogramo = 1000
    # Litro = 1000
    # Libra = 453.59
    factor = models.DecimalField(max_digits=10, decimal_places=4, default=1, help_text="1 para Gramos/ML. 1000 para KG/L.")

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

class CategoriaInsumo(models.Model):
    nombre = models.CharField(max_length=100)
    def __str__(self): return self.nombre

class Insumo(models.Model):
    nombre = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaInsumo, on_delete=models.SET_NULL, null=True)
    
    # La unidad base del insumo SIEMPRE debería ser la pequeña (Gramo / ML)
    unidad = models.ForeignKey(UnidadMedida, on_delete=models.PROTECT, verbose_name="Unidad Base (Almacén)")
    
    # Aumentamos precisión a 6 decimales porque el costo por gramo es muy pequeño (Ej: $0.00034)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=6, default=0, verbose_name="Costo x Gramo ($)")
    stock_actual = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=500) # Ej: 500 gramos
    
    es_materia_prima = models.BooleanField(default=True)
    es_insumo_compuesto = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre} ({self.unidad.codigo})"
    
    @property
    def valor_total_invertido(self):
        return round(self.stock_actual * self.costo_unitario, 2)

    def calcular_costo_desde_subreceta(self):
        if not self.es_insumo_compuesto: return
        total = 0
        for componente in self.componentes.all():
            total += float(componente.cantidad) * float(componente.insumo_hijo.costo_unitario)
        self.costo_unitario = total
        self.save()

class IngredienteCompuesto(models.Model):
    insumo_padre = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='componentes')
    insumo_hijo = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name='usado_en_compuestos')
    cantidad = models.DecimalField(max_digits=10, decimal_places=4) # Cantidad en gramos

class MovimientoInventario(models.Model):
    TIPOS_MOVIMIENTO = [('ENTRADA', 'Compra'), ('SALIDA', 'Consumo'), ('AJUSTE', 'Ajuste')]
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=TIPOS_MOVIMIENTO)
    
    # DATOS DE LA COMPRA (LO QUE ESCRIBE EL USUARIO)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Cantidad Comprada")
    
    # NUEVO: En qué unidad lo compraste (Ej: Compré en KG)
    unidad_movimiento = models.ForeignKey(UnidadMedida, on_delete=models.SET_NULL, null=True, verbose_name="Unidad de Compra")
    
    costo_unitario_movimiento = models.DecimalField(max_digits=12, decimal_places=4, default=0, verbose_name="Costo por Unidad de Compra")
    
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    nota = models.CharField(max_length=255, blank=True, null=True)

# --- LA MAGIA MATEMÁTICA (SEÑAL) ---
@receiver(post_save, sender=MovimientoInventario)
def actualizar_stock_conversion(sender, instance, created, **kwargs):
    if created:
        insumo = instance.insumo
        
        # 1. OBTENER FACTOR DE CONVERSIÓN
        # Si eligió KG, el factor es 1000. Si eligió Gramos, es 1.
        factor = instance.unidad_movimiento.factor if instance.unidad_movimiento else 1
        
        # 2. CONVERTIR A GRAMOS (Para el Stock)
        cantidad_en_gramos = instance.cantidad * factor
        
        # 3. CONVERTIR PRECIO A "POR GRAMO"
        # Si pagué $10 por 1KG (1000g) -> $10 / 1000 = $0.01 por gramo
        costo_por_gramo_nuevo = 0
        if instance.costo_unitario_movimiento > 0:
            costo_por_gramo_nuevo = instance.costo_unitario_movimiento / factor

        # 4. APLICAR AL INSUMO
        if instance.tipo == 'ENTRADA':
            insumo.stock_actual += cantidad_en_gramos
            # Actualizamos el costo base del insumo al nuevo precio por gramo
            if not insumo.es_insumo_compuesto and costo_por_gramo_nuevo > 0:
                insumo.costo_unitario = costo_por_gramo_nuevo

        elif instance.tipo == 'SALIDA':
            insumo.stock_actual -= cantidad_en_gramos
            if insumo.stock_actual < 0: insumo.stock_actual = 0

        elif instance.tipo == 'AJUSTE':
            insumo.stock_actual += cantidad_en_gramos
            if not insumo.es_insumo_compuesto and instance.cantidad > 0 and costo_por_gramo_nuevo > 0:
                insumo.costo_unitario = costo_por_gramo_nuevo

        insumo.save()