
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
            form.save()
            messages.success(request, "Concepto creado en el Maestro.")
            return redirect('maestro_list')
    else:
        form = MaestroInsumoForm()
    
    return render(request, 'maestros/maestro_form.html', {'form': form, 'titulo': 'Nuevo Concepto'})

# EDITAR (Desde el Maestro)
def maestro_edit(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk)
    if request.method == 'POST':
        form = MaestroInsumoForm(request.POST, instance=insumo)
        if form.is_valid():
            form.save() # Al guardar, se recalcula el costo con la merma automáticamente
            messages.success(request, "Concepto actualizado.")
            return redirect('maestro_list')
    else:
        form = MaestroInsumoForm(instance=insumo)
    
    return render(request, 'maestros/maestro_form.html', {'form': form, 'titulo': f'Editar {insumo.nombre}'})