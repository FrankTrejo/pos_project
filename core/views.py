from django.shortcuts import render, redirect
from .models import Configuracion
# IMPORTANTE: Importamos los 3 formularios nuevos, NO el viejo
from .forms import ConfigIdentidadForm, ConfigEconomiaForm, ConfigVisualForm
from django.contrib import messages

# 1. MENÚ PRINCIPAL
def configuracion_menu(request):
    config = Configuracion.get_solo()
    return render(request, 'core/configuracion_menu.html', {'config': config})

# 2. EDITAR IDENTIDAD
def editar_identidad(request):
    config = Configuracion.get_solo()
    
    if request.method == 'POST':
        form = ConfigIdentidadForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Identidad actualizada correctamente.')
            return redirect('configuracion_menu')
    else:
        form = ConfigIdentidadForm(instance=config)
    
    return render(request, 'core/configuracion_form.html', {
        'form': form, 
        'titulo': 'Identidad del Negocio',
        'icono': 'fas fa-store'
    })

# 3. EDITAR ECONOMÍA
def editar_economia(request):
    config = Configuracion.get_solo()
    
    if request.method == 'POST':
        form = ConfigEconomiaForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tasas y Costos actualizados.')
            return redirect('configuracion_menu')
    else:
        form = ConfigEconomiaForm(instance=config)

    return render(request, 'core/configuracion_form.html', {
        'form': form, 
        'titulo': 'Economía y Costos',
        'icono': 'fas fa-chart-line'
    })

# 4. EDITAR APARIENCIA
def editar_visual(request):
    config = Configuracion.get_solo()
    
    if request.method == 'POST':
        form = ConfigVisualForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Apariencia actualizada.')
            return redirect('configuracion_menu')
    else:
        form = ConfigVisualForm(instance=config)

    return render(request, 'core/configuracion_form.html', {
        'form': form, 
        'titulo': 'Apariencia y Tickets',
        'icono': 'fas fa-image'
    })

