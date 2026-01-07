from django.db import models

class Configuracion(models.Model):
    # --- 1. IDENTIDAD DEL NEGOCIO (Para el Ticket) ---
    nombre_empresa = models.CharField(max_length=100, default="Di Catia Pizzas")
    rif = models.CharField(max_length=20, default="J-00000000-0", verbose_name="RIF / ID Fiscal")
    direccion = models.TextField(blank=True, default="Caracas, Venezuela")
    telefono = models.CharField(max_length=50, blank=True)
    mensaje_ticket = models.CharField(max_length=200, default="¡Gracias por su compra!", help_text="Mensaje al final de la factura")
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)

    # --- 2. MONEDA E IMPUESTOS ---
    tasa_dolar = models.DecimalField(max_digits=10, decimal_places=2, default=40.00, verbose_name="Tasa BCV ($)")
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=16.00, verbose_name="% IVA")
    
    # --- 3. COSTOS ADICIONALES (LO QUE PEDISTE) ---
    # Cargos al Cliente
    igtf_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=3.00, verbose_name="% IGTF (Divisas)")
    servicio_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, verbose_name="% Servicio / Propina")
    monto_delivery_fijo = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Costo Delivery Estándar ($)")
    
    # Costos Operativos (Para cálculo de ganancia real)
    costo_caja_pequena = models.DecimalField(max_digits=10, decimal_places=2, default=0.50, verbose_name="Costo Caja Pequeña ($)")
    costo_caja_grande = models.DecimalField(max_digits=10, decimal_places=2, default=0.80, verbose_name="Costo Caja Grande ($)")
    gastos_operativos_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, help_text="% estimado de Luz, Gas, Alquiler por producto", verbose_name="% Gastos Operativos")

    def __str__(self):
        return "Configuración General"

    class Meta:
        verbose_name = "Configuración"
        verbose_name_plural = "Configuración"

    # --- MÉTODO MÁGICO SINGLETON ---
    # Esto asegura que siempre llamemos a la misma configuración (ID=1)
    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj

    # Evitar crear más de un registro
    def save(self, *args, **kwargs):
        self.pk = 1
        super(Configuracion, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass # No permitir borrar la configuración