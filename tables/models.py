from django.db import models
from django.contrib.auth.models import User
from inventory.models import Insumo
from decimal import Decimal
from inventory.models import Insumo
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from inventory.models import Insumo 
from django.db import models

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
    solicitud_pago = models.BooleanField(default=False, verbose_name="¿Pidió Cuenta?")
    
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
        ('EFECTIVO_USD', 'Efectivo ($)'),
        ('EFECTIVO_BS', 'Efectivo (Bs)'),
        ('PAGO_MOVIL', 'Pago Móvil'),
        ('PUNTO', 'Punto de Venta'),
        ('ZELLE', 'Zelle'),
        ('MIXTO', 'Mixto'),
    ]
    
    fecha = models.DateTimeField(auto_now_add=True)
    codigo_factura = models.CharField(max_length=20, unique=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Total Facturado")
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO)
    mesero = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ventas_realizadas')
    mesa_numero = models.IntegerField()

    # --- CAMPOS NUEVOS PARA EL FLUJO DE CAJA ---
    monto_recibido = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Cuánto dinero entregó el cliente")
    propina = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Monto excedente asignado a propina")
    # El vuelto se calcula: (monto_recibido - total - propina)

    # === PEGAR ESTO AQUÍ ===
    anulada = models.BooleanField(default=False, verbose_name="¿Venta Anulada?")
    motivo_anulacion = models.CharField(max_length=200, blank=True, null=True)
    fecha_anulacion = models.DateTimeField(blank=True, null=True)
    usuario_anulacion = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ventas_anuladas')
    # =======================

    def __str__(self):
        estado = " (ANULADA)" if self.anulada else ""
        return f"Factura #{self.codigo_factura}{estado}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    nombre_producto = models.CharField(max_length=100) # Guardamos el nombre por si borran el producto luego
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad}x {self.nombre_producto}"
    
# 1. ORDEN TEMPORAL (La cuenta abierta)
class Orden(models.Model):
    mesa = models.OneToOneField(Table, on_delete=models.CASCADE, related_name='orden_activa')
    mesero = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    # Guardamos si ya se imprimió para saber si es "Comanda nueva" o "Reimpresión"
    impreso = models.BooleanField(default=False) 
    # --- AGREGAR ESTO ---
    TIPO_OPCIONES = [
        ('MESA', 'Comer en Mesa'),
        ('LLEVAR', 'Para Llevar'),
        ('DOMICILIO', 'Domicilio'),
    ]
    
    tipo_servicio = models.CharField(
        max_length=20, 
        choices=TIPO_OPCIONES, 
        default='MESA',
        verbose_name="Tipo de Servicio"
    )

    def __str__(self):
        return f"Orden Mesa {self.mesa.number}"
    
    @property
    def total_calculado(self):
        return sum(d.subtotal for d in self.detalles.all())

# 2. DETALLE DE LA ORDEN (Qué pidieron)
class DetalleOrden(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2) # Precio al momento de pedir
    nota = models.CharField(max_length=200, blank=True, null=True) # Ej: "Sin cebolla"

    # --- NUEVO CAMPO ---
    es_para_llevar = models.BooleanField(default=False, verbose_name="¿Para Llevar?")
    
    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

class DetalleOrdenExtra(models.Model):
    detalle_orden = models.ForeignKey(DetalleOrden, on_delete=models.CASCADE, related_name='extras_elegidos')
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT, verbose_name="Ingrediente Extra")
    precio = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio cobrado por el extra")

    def __str__(self):
        return f"Extra {self.insumo.nombre} en {self.detalle_orden.producto.nombre}"
    
class Pago(models.Model):
    METODOS = [
        ('EFECTIVO_USD', 'Efectivo ($)'),
        ('EFECTIVO_BS', 'Efectivo (Bs)'), # Opcional, si quieres registrarlo separado
        ('PAGO_MOVIL', 'Pago Móvil'),
        ('PUNTO', 'Punto de Venta'),
        ('ZELLE', 'Zelle'),
    ]
    
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='pagos')
    metodo = models.CharField(max_length=20, choices=METODOS)
    monto = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monto abonado en USD")
    referencia = models.CharField(max_length=50, blank=True, null=True, help_text="Ref bancaria si aplica")

    def __str__(self):
        return f"{self.get_metodo_display()}: ${self.monto}"
    
# tables/models.py

class DetalleVentaExtra(models.Model):
    detalle_venta = models.ForeignKey(DetalleVenta, related_name='extras', on_delete=models.CASCADE)
    nombre_extra = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Extra {self.nombre_extra} en venta {self.detalle_venta.id}"
    

class PrecioExtra(models.Model):
    TAMANOS = [
        ('IND', 'Individual'),
        ('MED', 'Mediana'),
        ('FAM', 'Familiar'),
    ]

    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE, related_name='precios_extra')
    tamano = models.CharField(max_length=3, choices=TAMANOS)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('insumo', 'tamano') 
        verbose_name = "Precio de Extra"
        verbose_name_plural = "Precios de Extras"

    def __str__(self):
        return f"{self.insumo.nombre} ({self.tamano}) - ${self.precio}"