# dashboard/views.py
from django.shortcuts import render

def panel_control(request):
    # En el futuro, aquí consultarías la BD para obtener los números reales
    # (ej. conteo de productos, total de ventas hoy, etc.)
    return render(request, 'dashboard/panel.html')