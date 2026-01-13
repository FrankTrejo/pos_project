# core/context_processors.py
from .models import Configuracion

def configuracion_global(request):
    # Esto hace que la variable {{ config }} esté disponible en TODOS los HTML
    return {
        'config': Configuracion.get_solo()
    }