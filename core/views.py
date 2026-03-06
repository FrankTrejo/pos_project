from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Configuracion
# Importamos los formularios que arreglamos antes
from .forms import ConfigIdentidadForm, ConfigEconomiaForm, ConfigVisualForm

# 1. MENÚ PRINCIPAL
def configuracion_menu(request):
    return render(request, 'core/configuracion_menu.html')

# 2. VISTA DE IDENTIDAD
def conf_identidad(request):
    config, created = Configuracion.objects.get_or_create(id=1)
    if request.method == 'POST':
        form = ConfigIdentidadForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos de Identidad actualizados.")
            return redirect('conf_identidad')
    else:
        form = ConfigIdentidadForm(instance=config)
    
    return render(request, 'core/configuracion_form.html', {
        'form': form, 'titulo': 'Identidad del Negocio'
    })

# 3. VISTA DE ECONOMÍA (La que te daba error)
def conf_economia(request):
    config, created = Configuracion.objects.get_or_create(id=1)
    if request.method == 'POST':
        form = ConfigEconomiaForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos Económicos actualizados.")
            return redirect('conf_economia')
    else:
        form = ConfigEconomiaForm(instance=config)
    
    return render(request, 'core/configuracion_form.html', {
        'form': form, 'titulo': 'Configuración Económica'
    })

# 4. VISTA VISUAL / IMPRESIÓN
def conf_visual(request):
    config, created = Configuracion.objects.get_or_create(id=1)
    if request.method == 'POST':
        form = ConfigVisualForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración Visual e Impresión actualizada.")
            return redirect('conf_visual')
    else:
        form = ConfigVisualForm(instance=config)
    
    return render(request, 'core/configuracion_form.html', {
        'form': form, 'titulo': 'Apariencia e Impresión'
    })