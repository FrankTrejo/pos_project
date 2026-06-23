from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# ... tus otros modelos si los hay ...

class AuditoriaEliminacion(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    usuario_responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Quién eliminó")
    mesa_numero = models.IntegerField()
    mesero_asignado = models.CharField(max_length=100, blank=True, null=True)
    
    # Guardamos el contenido como texto plano para que no dependa de otras tablas
    resumen_pedido = models.TextField(help_text="Lista de productos que tenía la mesa")
    total_eliminado = models.DecimalField(max_digits=10, decimal_places=2)
    
    motivo = models.CharField(max_length=255, verbose_name="Motivo de eliminación")

    def __str__(self):
        return f"Eliminación Mesa {self.mesa_numero} - ${self.total_eliminado}"

class AuditoriaConfiguracion(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Usuario responsable")
    accion = models.CharField(max_length=255, verbose_name="Acción Realizada")
    detalles = models.TextField(verbose_name="Detalles del Cambio")

    def __str__(self):
        return f"{self.fecha.strftime('%d/%m/%Y %H:%M')} - {self.accion}"
    
class CuadreCaja(models.Model):
    fecha_hora = models.DateTimeField(auto_now_add=True)
    fecha_cuadre = models.DateField(default=timezone.now)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Efectivo
    sistema_efectivo_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fisico_efectivo_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    sistema_efectivo_bs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fisico_efectivo_bs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Electrónicos
    sistema_electronico_bs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fisico_electronico_bs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    sistema_electronico_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fisico_electronico_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notas = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"Cuadre #{self.id} - {self.fecha_cuadre.strftime('%d/%m/%Y')}"

    @property
    def diferencia_efectivo_usd(self):
        return self.fisico_efectivo_usd - self.sistema_efectivo_usd

    @property
    def diferencia_efectivo_bs(self):
        return self.fisico_efectivo_bs - self.sistema_efectivo_bs
