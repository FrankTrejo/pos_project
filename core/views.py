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
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Configuracion
from .forms import ConfigEconomiaForm, CostoAdicionalForm # Importamos el nuevo form
from tables.models import CostoAdicional # Importamos tu modelo existente

def editar_economia(request):
    # --- LOGICA 1: BORRAR UN COSTO ---
    if request.method == 'POST' and 'delete_costo' in request.POST:
        try:
            costo_id = request.POST.get('costo_id')
            CostoAdicional.objects.filter(id=costo_id).delete()
            messages.warning(request, 'Costo eliminado del maestro.')
        except Exception as e:
            messages.error(request, f'Error al eliminar: {e}')
        return redirect('editar_economia')

    # --- LOGICA 2: AGREGAR NUEVO COSTO ---
    if request.method == 'POST' and 'add_costo' in request.POST:
        form_costo = CostoAdicionalForm(request.POST)
        if form_costo.is_valid():
            form_costo.save()
            messages.success(request, 'Nuevo costo agregado correctamente.')
            return redirect('editar_economia')
        else:
            messages.error(request, 'Error al agregar. Verifica los datos.')
    
    else:
        # GET: Formulario limpio
        form_costo = CostoAdicionalForm()

    # --- LOGICA 3: LISTAR ---
    lista_costos = CostoAdicional.objects.all().order_by('nombre')

    return render(request, 'core/configuracion_economia.html', {
        'form_costo': form_costo,
        'lista_costos': lista_costos,
        'titulo': 'Gestión de Costos Indirectos',
    })
    config = Configuracion.get_solo()
    
    # --- LOGICA 1: BORRAR UN COSTO EXISTENTE ---
    if request.method == 'POST' and 'delete_costo' in request.POST:
        try:
            costo_id = request.POST.get('costo_id')
            CostoAdicional.objects.filter(id=costo_id).delete()
            messages.warning(request, 'Costo eliminado del maestro.')
        except Exception as e:
            messages.error(request, f'Error al eliminar: {e}')
        return redirect('editar_economia')

    # --- LOGICA 2: PROCESAR FORMULARIOS ---
    if request.method == 'POST':
        
        # A) Si estamos guardando la configuración del Dólar/IVA
        if 'save_config' in request.POST:
            form_config = ConfigEconomiaForm(request.POST, instance=config)
            form_costo = CostoAdicionalForm() # Form vacío
            if form_config.is_valid():
                form_config.save()
                messages.success(request, 'Indicadores globales actualizados.')
                return redirect('editar_economia')

        # B) Si estamos agregando un Costo Adicional Nuevo
        elif 'add_costo' in request.POST:
            form_config = ConfigEconomiaForm(instance=config) # Mantener datos config
            form_costo = CostoAdicionalForm(request.POST)
            if form_costo.is_valid():
                form_costo.save()
                messages.success(request, 'Nuevo costo agregado al maestro.')
                return redirect('editar_economia')
    
    else:
        # GET: Cargar formularios limpios
        form_config = ConfigEconomiaForm(instance=config)
        form_costo = CostoAdicionalForm()

    # --- LOGICA 3: TRAER LA LISTA PARA LA TABLA ---
    lista_costos = CostoAdicional.objects.all().order_by('nombre')

    # Renderizamos el template (que te doy abajo)
    return render(request, 'core/configuracion_economia.html', {
        'form_config': form_config,
        'form_costo': form_costo,
        'lista_costos': lista_costos,
        'titulo': 'Economía y Costos Adicionales',
        'icono': 'fas fa-chart-line'
    })
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

