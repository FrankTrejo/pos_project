from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from inventory.models import Insumo
from .forms import MaestroInsumoForm

# VISTA PRINCIPAL: TABLA TIPO EXCEL
def maestro_list(request):
    insumos = Insumo.objects.all().order_by('nombre')
    
    # Simulamos una tasa de cambio (podrías guardarla en BD luego)
    tasa_dolar = 300.00 
    
    return render(request, 'maestros/maestro_list.html', {
        'insumos': insumos,
        'tasa': tasa_dolar
    })

# CREAR NUEVO (Desde el Maestro)
def maestro_create(request):
    if request.method == 'POST':
        form = MaestroInsumoForm(request.POST)
        if form.is_valid():
            try:
                insumo = form.save()
                messages.success(request, f"Concepto '{insumo.nombre}' creado exitosamente.")
                return redirect('maestro_list')
            except Exception as e:
                messages.error(request, f"Error de base de datos: {e}")
        else:
            # --- CORRECCIÓN IMPORTANTE ---
            # Si no entra al if, cae aquí y te avisa por qué
            print("⚠️ ERROR DE VALIDACIÓN:", form.errors) # Mira tu terminal negra
            messages.error(request, "El formulario tiene errores. Revisa los campos en rojo.")
    else:
        form = MaestroInsumoForm()
    
    return render(request, 'maestros/maestro_form.html', {'form': form, 'titulo': 'Nuevo Concepto'})

# EDITAR (Desde el Maestro)
def maestro_edit(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk)
    
    if request.method == 'POST':
        form = MaestroInsumoForm(request.POST, instance=insumo)
        if form.is_valid():
            try:
                form.save() # Al guardar, se recalcula el costo automáticamente
                messages.success(request, "Concepto actualizado correctamente.")
                return redirect('maestro_list')
            except Exception as e:
                messages.error(request, f"Error al guardar: {e}")
        else:
            # --- CORRECCIÓN IMPORTANTE ---
            print("⚠️ ERROR EN EDICIÓN:", form.errors)
            messages.error(request, "No se pudo actualizar. Verifica los datos ingresados.")
    else:
        form = MaestroInsumoForm(instance=insumo)
    
    return render(request, 'maestros/maestro_form.html', {'form': form, 'titulo': f'Editar {insumo.nombre}'})