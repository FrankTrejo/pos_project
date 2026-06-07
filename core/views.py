from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Configuracion
# Importamos los formularios que arreglamos antes
from .forms import ConfigIdentidadForm, CostoAdicionalForm, ConfigVisualForm, ConfigProcesosForm
from tables.models import TasaBCV, CostoAdicional
from reports.models import AuditoriaConfiguracion
from django.db.models import ProtectedError
from django.core.paginator import Paginator

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
    # Obtenemos los costos ordenados desde el más nuevo al más viejo
    costos_list = CostoAdicional.objects.all().order_by('-id')
    paginator = Paginator(costos_list, 10) # 10 registros por página
    
    page_number = request.GET.get('page')
    costos = paginator.get_page(page_number)
    
    if request.method == 'POST':
        if 'delete_costo' in request.POST:
            costo_id = request.POST.get('costo_id')
            try:
                costo = CostoAdicional.objects.get(id=costo_id)
                nombre = costo.nombre
                costo.delete()
                messages.success(request, f"Costo '{nombre}' eliminado exitosamente.")
            except ProtectedError:
                messages.error(request, "No se puede eliminar porque este costo ya está asignado a uno o más productos.")
            except Exception as e:
                messages.error(request, f"Error al eliminar: {str(e)}")
            return redirect('conf_economia')
            
        form = CostoAdicionalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Costo adicional registrado exitosamente.")
            return redirect('conf_economia')
    else:
        form = CostoAdicionalForm()
    
    return render(request, 'core/configuracion_economia.html', {
        'form_costo': form, 
        'titulo': 'Costos Adicionales / Economía',
        'costos': costos
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
    
    # Guardar valores anteriores para la auditoría
    old_scraping = config.usar_scraping_bcv
    old_tasa = config.tasa_dolar
    
    if request.method == 'POST':
        form = ConfigProcesosForm(request.POST, instance=config)
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
                    accion="Actualización de Procesos y Tasa",
                    detalles=" | ".join(cambios)
                )
            
            messages.success(request, "Automatización y Procesos actualizados.")
            return redirect('configuracion_menu')
    else:
        form = ConfigProcesosForm(instance=config)
    
    # Obtener última tasa escrapeada para enviarla al JavaScript si es necesario
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_scraped = float(tasa_obj.precio) if tasa_obj else float(config.tasa_dolar)
    
    return render(request, 'core/configuracion_form.html', {
        'form': form, 'titulo': 'Automatización y Procesos', 'icono': 'fas fa-cogs', 'tasa_scraped': tasa_scraped
    })

def costo_indirecto_edit(request, pk):
    costo = get_object_or_404(CostoAdicional, pk=pk)
    if request.method == 'POST':
        form = CostoAdicionalForm(request.POST, instance=costo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Costo '{costo.nombre}' actualizado correctamente.")
            return redirect('conf_economia')
    else:
        form = CostoAdicionalForm(instance=costo)
    
    return render(request, 'core/configuracion_form.html', {
        'form': form, 'titulo': f'Editar Costo: {costo.nombre}', 'icono': 'fas fa-edit'
    })