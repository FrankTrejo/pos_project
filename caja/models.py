from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class CuadreCaja(models.Model):
    fecha_hora = models.DateTimeField(auto_now_add=True)
    fecha_cuadre = models.DateField(default=timezone.now)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # --- TASAS DEL DÍA ---
    tasa_general = models.DecimalField(max_digits=12, decimal_places=2, default=1.0)
    tasa_cashea = models.DecimalField(max_digits=12, decimal_places=2, default=1.0)
    
    # --- VALORES DEL SISTEMA (ESPERADOS) ---
    ventas_sistema_general = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total ventas sin Cashea")
    ventas_sistema_cashea = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total ventas por Cashea")
    total_ventas_sistema = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fondo_caja_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Fondo de Caja USD")
    
    # --- VALORES CONTADOS POR EL CAJERO ($) ---
    dolares_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cashea_recibido_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cashea_financiado_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gastos_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # --- VALORES CONTADOS POR EL CAJERO (BS) ---
    punto_venta_bs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    efectivo_bs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pago_movil_bs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gastos_bs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # --- RESULTADOS FINALES EN $ ---
    total_recibido_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_esperado_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    diferencia_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Positivo si sobra, negativo si falta")
    
    notas = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"Cuadre #{self.id} - {self.fecha_cuadre.strftime('%d/%m/%Y')}"

    @property
    def diferencia_efectivo_usd(self):
        return self.diferencia_usd