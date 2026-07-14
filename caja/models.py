from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class CuadreCaja(models.Model):
    fecha_hora = models.DateTimeField(auto_now_add=True)
    fecha_cuadre = models.DateField(default=timezone.now)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # --- VALORES DEL SISTEMA ---
    total_ventas_dia = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fondo_caja_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Fondo de Caja USD")
    gastos_turno_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Gastos del Turno USD")
    
    # --- VALORES CONTADOS POR EL CAJERO ---
    recibido_efectivo_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    recibido_efectivo_bs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    recibido_electronico_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    recibido_electronico_bs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # --- RESULTADO ---
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