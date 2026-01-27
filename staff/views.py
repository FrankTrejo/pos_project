from django.shortcuts import render

# Create your views here.
# staff/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from .forms import PersonalForm

# Función auxiliar para asegurar que existan los grupos básicos
def asegurar_grupos():
    Group.objects.get_or_create(name='Administrador')
    Group.objects.get_or_create(name='Mesero')
    Group.objects.get_or_create(name='Cajero')

@staff_member_required
def staff_list(request):
    asegurar_grupos() # Crea los grupos si es la primera vez que entras
    # Traemos todos los usuarios y pre-cargamos sus grupos para no hacer muchas consultas
    usuarios = User.objects.all().prefetch_related('groups').order_by('username')
    return render(request, 'staff/staff_list.html', {'usuarios': usuarios})

@staff_member_required
def staff_create(request):
    if request.method == 'POST':
        form = PersonalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario creado correctamente.")
            return redirect('staff_list')
    else:
        form = PersonalForm()
    
    return render(request, 'staff/staff_form.html', {'form': form, 'titulo': 'Crear Personal'})

@staff_member_required
def staff_edit(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = PersonalForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, "Usuario actualizado correctamente.")
            return redirect('staff_list')
    else:
        form = PersonalForm(instance=usuario)
    
    return render(request, 'staff/staff_form.html', {'form': form, 'titulo': f'Editar: {usuario.username}'})

@staff_member_required
def staff_delete(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if usuario.is_superuser and User.objects.filter(is_superuser=True).count() == 1:
            messages.error(request, "No puedes eliminar al último Superusuario.")
        else:
            usuario.delete()
            messages.success(request, "Usuario eliminado.")
    return redirect('staff_list')