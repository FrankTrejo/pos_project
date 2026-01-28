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
    precio_venta_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Precio de Venta Extra ($)")
    cantidad_porcion_extra = models.DecimalField(max_digits=10, decimal_places=4, default=0.00, help_text="Cantidad a descontar por cada extra vendido (Ej: 0.050 para 50g)")

    # --- MAESTRO DE COSTOS (LÓGICA CORREGIDA) ---
    # Ahora definimos el peso del "bulto" o "unidad de compra"
    peso_standar = models.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        default=1, 
        verbose_name="Peso por Unidad de Compra (Gr/Ml)"
    )
    # Ejemplo: Saco de Harina = 25000 (gr)
    
    precio_mercado = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Costo de la Unidad ($)")
    # Ejemplo: Precio del Saco = $45.00
    
    merma_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="% Merma")
    
    # --- RENDIMIENTO (SE CALCULA AUTOMÁTICO) ---
    rendimiento = models.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        default=1, 
        verbose_name="Rendimiento (Cantidad Final Producida)"
    )

    # COSTO Y STOCK
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=6, default=0, verbose_name="Costo Real x Gramo")
    stock_actual = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=500)
    es_insumo_compuesto = models.BooleanField(default=False)

    def __str__(self): return f"{self.nombre}"
    
    @property
    def valor_total_invertido(self):
        return round(self.stock_actual * self.costo_unitario, 2)

    # --- MÉTODO 1: CÁLCULO AUTOMÁTICO DE RECETAS ---
    # inventory/models.py

    # inventory/models.py

    def calcular_costo_desde_subreceta(self):
        """
        LÓGICA BLINDADA PARA RECETAS:
        Calcula cuánto cuesta 1 GRAMO de la receta final.
        Fórmula: (Costo Total de Ingredientes) / (Peso Total de la Receta)
        """
        # 1. VALIDACIÓN: Solo aplica si es Compuesto (Receta)
        if not self.es_insumo_compuesto:
            return

        total_costo_fabricacion = Decimal(0)
        total_peso_calculado = Decimal(0)

        # 2. SUMAR COSTOS Y PESOS DE LOS INGREDIENTES
        for componente in self.componentes.all():
            # Cuánto cuesta esta cantidad de ingrediente (Ej: 2500g Tomate * Precio Tomate)
            costo_linea = componente.cantidad * componente.insumo_hijo.costo_unitario
            total_costo_fabricacion += costo_linea
            
            # Cuánto pesa este ingrediente
            total_peso_calculado += componente.cantidad

        # 3. DETERMINAR EL PESO FINAL (EL DIVISOR)
        # Si definiste manualmente que la receta rinde 2700g (rendimiento), usamos eso.
        # Si no, usamos la suma de los ingredientes.
        if self.rendimiento > 1:
            peso_final = self.rendimiento
        else:
            peso_final = total_peso_calculado
            # Guardamos este peso calculado como rendimiento
            self.rendimiento = peso_final

        # 4. APLICAR LA FÓRMULA (DIVISIÓN)
        # AQUÍ ESTÁ LA SOLUCIÓN: Costo Total / Peso Total = Costo Unitario
        if peso_final > 0:
            self.costo_unitario = total_costo_fabricacion / peso_final
        else:
            self.costo_unitario = 0

        # 5. GUARDAR EN BASE DE DATOS
        # Usamos update para ser directos y evitar bucles
        Insumo.objects.filter(pk=self.pk).update(
            costo_unitario=self.costo_unitario,
            rendimiento=self.rendimiento
        )
        """
        Lógica Blindada:
        1. Suma todo lo que gastaste en ingredientes (Costo de Fabricación).
        2. Suma todo lo que pesan los ingredientes (Peso Total).
        3. REALIZA LA DIVISIÓN: Costo / Peso = Precio Real por Gramo.
        """
        # SOLO APLICA PARA COMPUESTOS (RECETAS)
        if not self.es_insumo_compuesto:
            return

        total_costo_fabricacion = Decimal(0)
        total_peso_resultante = Decimal(0)

        # 1. Sumamos costo y peso de los ingredientes
        for componente in self.componentes.all():
            total_costo_fabricacion += componente.cantidad * componente.insumo_hijo.costo_unitario
            total_peso_resultante += componente.cantidad

        # 2. VALIDACIÓN DE PESO (DIVISOR)
        # Si el usuario configuró manualmente que la receta rinde 2000g, usamos eso.
        # Si no, usamos la suma automática de los ingredientes.
        if self.rendimiento > 1:
            peso_final_divisor = self.rendimiento
        else:
            peso_final_divisor = total_peso_resultante
            # Actualizamos el rendimiento automáticamente si estaba en 0
            self.rendimiento = peso_final_divisor

        # 3. LA VALIDACIÓN QUE PEDISTE (CÁLCULO FINAL)
        # Si es compuesto, JAMÁS guardamos el costo total ($13) como unitario.
        # Siempre dividimos entre el peso ($13 / 1000g = $0.013).
        
        if peso_final_divisor > 0:
            self.costo_unitario = total_costo_fabricacion / peso_final_divisor
        else:
            self.costo_unitario = 0

        # Guardamos en BD usando update para no disparar bucles
        Insumo.objects.filter(pk=self.pk).update(
            costo_unitario=self.costo_unitario,
            rendimiento=self.rendimiento
        )
        """
        Calcula el costo unitario real (por gramo/ml) de una receta.
        Fórmula: Costo Total de Ingredientes / Rendimiento Total.
        """
        if not self.es_insumo_compuesto:
            return

        # 1. Calcular Costo Total del Lote ($)
        # (Cuánto cuesta la olla completa con todos los ingredientes)
        total_costo_lote = Decimal(0)
        total_peso_ingredientes = Decimal(0)

        for componente in self.componentes.all():
            total_costo_lote += componente.cantidad * componente.insumo_hijo.costo_unitario
            total_peso_ingredientes += componente.cantidad

        # 2. Definir el Divisor (Rendimiento)
        # VALIDACIÓN IMPORTANTE: 
        # Si el usuario configuró un rendimiento manual (ej: 2700g) usamos ese.
        # Si no (está en 0 o 1), usamos la suma de los pesos de los ingredientes.
        if self.rendimiento > 1: 
            peso_final = self.rendimiento
        else:
            peso_final = total_peso_ingredientes
            # Si calculamos el peso sumando, actualizamos el campo rendimiento para referencia
            if peso_final > 0:
                self.rendimiento = peso_final

        # 3. CÁLCULO DEL PRECIO POR GRAMO (Tu validación solicitada)
        # Nunca guardamos el precio de fabricación directo. Siempre dividimos.
        if peso_final > 0:
            nuevo_costo_unitario = total_costo_lote / peso_final
        else:
            # Si no hay peso (receta vacía), el costo unitario es 0
            nuevo_costo_unitario = 0

        # 4. Guardar en Base de Datos
        # Usamos .update() para ser eficientes y evitar bucles de señales
        Insumo.objects.filter(pk=self.pk).update(
            costo_unitario=nuevo_costo_unitario,
            rendimiento=self.rendimiento
        )
        if not self.es_insumo_compuesto:
            return

        total_costo = Decimal('0.0')
        total_peso_teorico = Decimal('0.0') 
        
        # Recorremos los ingredientes
        for componente in self.componentes.all():
            # 1. Sumar Costo ($)
            total_costo += componente.cantidad * componente.insumo_hijo.costo_unitario
            
            # 2. Sumar Peso (Gramos/ML) - AUTOMÁTICO
            total_peso_teorico += componente.cantidad
            
        # 3. Asignamos el rendimiento calculado automáticamente
        self.rendimiento = total_peso_teorico 

        # 4. Cálculo del Costo Unitario (Costo Total / Peso Total)
        if total_peso_teorico > 0:
            nuevo_costo_unitario = total_costo / total_peso_teorico
        else:
            nuevo_costo_unitario = total_costo 

        # Actualizamos la base de datos directamente
        Insumo.objects.filter(pk=self.pk).update(
            costo_unitario=nuevo_costo_unitario,
            rendimiento=total_peso_teorico
        )
    
    # --- MÉTODO 2: CÁLCULO DESDE EL MAESTRO (MATERIA PRIMA) ---
    def save(self, *args, **kwargs):
        # Si NO es receta (es materia prima: Harina, Tomate, etc)
        if not self.es_insumo_compuesto:
            # Fórmula: Costo Unitario = Precio del Saco / Peso del Saco
            # Aplicamos la merma si existe (a mayor merma, mayor costo real)
            
            if self.precio_mercado > 0 and self.peso_standar > 0:
                costo_base = self.precio_mercado / self.peso_standar
                
                factor_merma = 1 - (self.merma_porcentaje / 100)
                
                if factor_merma > 0:
                    self.costo_unitario = costo_base / factor_merma
                else:
                    self.costo_unitario = costo_base
            else:
                # Si no hay datos, mantenemos el costo en 0 o el anterior
                pass

        super().save(*args, **kwargs)

        # Si ES receta, recalculamos después de guardar por seguridad
        if self.es_insumo_compuesto:
            self.calcular_costo_desde_subreceta()

    es_extra = models.BooleanField(
        default=False, 
        verbose_name="¿Se vende como Extra?",
        help_text="Marca esta casilla si este ingrediente puede ser agregado como extra en un producto."
    )

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

# --- SEÑAL DE ACTUALIZACIÓN DE STOCK ---
@receiver(post_save, sender=MovimientoInventario)
def actualizar_stock_conversion(sender, instance, created, **kwargs):
    if created:
        insumo = instance.insumo
        # Si hay factor de conversión (ej: Kilos a Gramos), lo aplicamos
        factor = instance.unidad_movimiento.factor if instance.unidad_movimiento else 1
        
        # Obtenemos la cantidad real en la unidad base (Gramos/ML)
        # Usamos abs() para asegurar que el número sea positivo y la matemática la decidimos abajo
        cantidad_en_gramos = abs(instance.cantidad * factor)
        
        # --- LÓGICA CORREGIDA ---
        
        if instance.tipo == 'ENTRADA':
            # COMPRAS: SUMAN (+)
            insumo.stock_actual += cantidad_en_gramos

        elif instance.tipo == 'SALIDA':
            # CONSUMO/MERMA: RESTAN (-)
            insumo.stock_actual -= cantidad_en_gramos
            
        elif instance.tipo == 'AJUSTE':
            # AJUSTE: DEPENDE DEL SIGNO
            # Si en la vista mandamos un negativo, resta. Si es positivo, suma.
            # Pero como la vista manda el número tal cual, vamos a asumir que:
            # AJUSTE POSITIVO = SUMA (Corrección de sobrante)
            # Para restar usando ajuste, tendríamos que permitir negativos en la vista.
            # Por seguridad, trataremos el AJUSTE igual que una ENTRADA (Suma).
            # SI QUIERES RESTAR, USA "SALIDA".
            insumo.stock_actual += instance.cantidad * factor

        # Evitamos stock negativo
        if insumo.stock_actual < 0:
            insumo.stock_actual = 0
            
        insumo.save()

class ConsumoInterno(models.Model):
    TIPOS = [
        ('PERSONAL', 'Comida de Personal'),
        ('CORTESIA', 'Cortesía / Regalo'),
        ('MERMA', 'Merma / Dañado'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPOS)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    descripcion = models.CharField(max_length=255) 
    costo_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.fecha.strftime('%d/%m')}"