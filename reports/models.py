from django.db import models
from django.contrib.auth.models import User

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