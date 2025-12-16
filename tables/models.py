from django.db import models
from django.contrib.auth.models import User
from inventory.models import Insumo
from decimal import Decimal
from inventory.models import Insumo
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
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

    # COSTO 1: Solo Ingredientes (Materia Prima)
    @property
    def costo_receta(self):
        total_costo = Decimal('0.00')
        for ingrediente in self.ingredientes.all():
            if ingrediente.insumo:
                total_costo += ingrediente.cantidad * ingrediente.insumo.costo_unitario
        return total_costo

    costo_materia_prima = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Costo Ingredientes ($)")

    def __str__(self):
        return f"{self.nombre} ({self.tamano})"
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
    
    # --- FUNCIÓN DE ACTUALIZACIÓN ---
    def actualizar_costo_receta(self):
        """Recorre los ingredientes y actualiza el campo costo_materia_prima"""
        total = Decimal('0.00')
        for ingrediente in self.ingredientes.all():
            if ingrediente.insumo:
                total += ingrediente.cantidad * ingrediente.insumo.costo_unitario
        
        self.costo_materia_prima = total
        self.save() # Guardamos el nuevo costo en la BD
    

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
        
@receiver([post_save, post_delete], sender=IngredienteProducto)
def update_costo_por_receta(sender, instance, **kwargs):
    # 'instance' es el IngredienteProducto
    if instance.producto:
        instance.producto.actualizar_costo_receta()

# SEÑAL 2: Si cambia el precio del INSUMO en Inventario -> Actualizar TODOS los productos que lo usen
@receiver(post_save, sender=Insumo)
def update_costo_por_insumo(sender, instance, **kwargs):
    # 'instance' es el Insumo (ej: Harina) que acaba de cambiar de precio
    
    # Buscamos todas las recetas que usan este insumo
    # (Usamos el 'related_name' por defecto o el set inverso)
    ingredientes_afectados = instance.ingredienteproducto_set.all()
    
    # Para cada ingrediente encontrado, le decimos a su producto que se recalcule
    for ingrediente in ingredientes_afectados:
        ingrediente.producto.actualizar_costo_receta()

# --- HISTORIAL DE VENTAS (Para Reportes) ---
class Venta(models.Model):
    METODOS_PAGO = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta / Débito'),
        ('PAGO_MOVIL', 'Pago Móvil'),
        ('ZELLE', 'Zelle'),
        ('OTRO', 'Otro'),
    ]

    fecha = models.DateTimeField(auto_now_add=True)
    codigo_factura = models.CharField(max_length=20, unique=True) # Ej: FAC-0001
    total = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO)
    mesero = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ventas_realizadas')
    mesa_numero = models.IntegerField(help_text="Número de mesa donde se originó")

    def __str__(self):
        return f"Venta {self.codigo_factura} - ${self.total}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    nombre_producto = models.CharField(max_length=100) # Guardamos el nombre por si borran el producto luego
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad}x {self.nombre_producto}"