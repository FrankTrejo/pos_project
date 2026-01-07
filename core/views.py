from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Configuracion
from .forms import ConfiguracionForm

def configuracion_view(request):
    # Obtenemos la única configuración existente (o la crea si no existe)
    config = Configuracion.get_solo()

    if request.method == 'POST':
        form = ConfiguracionForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "Configuración actualizada correctamente 💾")
            return redirect('configuracion')
    else:
        form = ConfiguracionForm(instance=config)

    return render(request, 'core/configuracion.html', {'form': form})