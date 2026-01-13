# core/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Rutas que SÍ puede ver el público (Excepciones)
        # Es vital poner aquí el login, logout y el admin para no crear un bucle infinito.
        rutas_publicas = [
            '/login/',
            '/logout/',
            '/admin/',  # El admin tiene su propio login, mejor dejarlo tranquilo
            '/media/',   # <--- AGREGA ESTA LÍNEA (Para que se vea el logo)
            '/static/',
        ]

        # 2. Lógica del Portero:
        # Si el usuario NO está autenticado...
        if not request.user.is_authenticated:
            # ... y la ruta actual NO empieza con ninguna de las permitidas...
            path = request.path
            es_publica = any(path.startswith(ruta) for ruta in rutas_publicas)
            
            if not es_publica:
                # ... ¡PA FUERA! Redirigir al login.
                return redirect('login')

        response = self.get_response(request)
        return response