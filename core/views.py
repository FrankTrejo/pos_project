from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Configuracion
# Importamos los formularios que arreglamos antes
from .forms import ConfigIdentidadForm, ConfigEconomiaForm, ConfigVisualForm, ConfigProcesosForm
from tables.models import TasaBCV
from reports.models import AuditoriaConfiguracion

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
            return redirect('configuracion_menu')
    else:
        form = ConfigIdentidadForm(instance=config)
    
    return render(request, 'core/configuracion_form.html', {
        'form': form, 'titulo': 'Identidad del Negocio'
    })

# 3. VISTA DE ECONOMÍA (La que te daba error)
def conf_economia(request):
    config, created = Configuracion.objects.get_or_create(id=1)
    
    # Guardar valores anteriores para la auditoría
    old_scraping = config.usar_scraping_bcv
    old_tasa = config.tasa_dolar
    
    if request.method == 'POST':
        form = ConfigEconomiaForm(request.POST, instance=config)
        if form.is_valid():
            nuevo_config = form.save(commit=False)
            
            # Detectar cambios
            cambios = []
            if old_scraping != nuevo_config.usar_scraping_bcv:
                estado = "Activado" if nuevo_config.usar_scraping_bcv else "Desactivado"
                cambios.append(f"Scraping automático {estado}")
            
            if old_tasa != nuevo_config.tasa_dolar:
                cambios.append(f"Tasa manual cambiada de {old_tasa} a {nuevo_config.tasa_dolar}")
            
            nuevo_config.save()
            
            # Registrar auditoría si hubo cambios
            if cambios:
                AuditoriaConfiguracion.objects.create(
                    usuario=request.user if request.user.is_authenticated else None,
                    accion="Actualización de Configuración Económica",
                    detalles=" | ".join(cambios)
                )
            
            messages.success(request, "Datos Económicos actualizados.")
            return redirect('configuracion_menu')
    else:
        form = ConfigEconomiaForm(instance=config)
    
    # Obtener última tasa escrapeada para enviarla al JavaScript
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_scraped = float(tasa_obj.precio) if tasa_obj else float(config.tasa_dolar)
    
    return render(request, 'core/configuracion_form.html', {
        'form': form, 
        'titulo': 'Configuración Económica',
        'tasa_scraped': tasa_scraped
    })

# 4. VISTA VISUAL / IMPRESIÓN
def conf_visual(request):
    config, created = Configuracion.objects.get_or_create(id=1)
    if request.method == 'POST':
        form = ConfigVisualForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración Visual e Impresión actualizada.")
            return redirect('configuracion_menu')
    else:
        form = ConfigVisualForm(instance=config)
    
    return render(request, 'core/configuracion_form.html', {
        'form': form, 'titulo': 'Apariencia e Impresión'
    })

# 5. VISTA PROCESOS Y AUTOMATIZACIÓN
def conf_procesos(request):
    config, created = Configuracion.objects.get_or_create(id=1)
    if request.method == 'POST':
        form = ConfigProcesosForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Automatización y Procesos actualizados.")
            return redirect('configuracion_menu')
    else:
        form = ConfigProcesosForm(instance=config)
    
    return render(request, 'core/configuracion_form.html', {
        'form': form, 'titulo': 'Automatización y Procesos', 'icono': 'fas fa-cogs'
    })