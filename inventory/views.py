from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Insumo, MovimientoInventario, CategoriaInsumo, IngredienteCompuesto
from .forms import InsumoForm, ComponenteForm, MovimientoInventarioForm
from django.db import models
import re
from decimal import Decimal  # <--- IMPORTANTE: Importamos el tipo de dato correcto

def inventory_index(request):
    """Muestra el listado de insumos con alertas de stock bajo"""
    insumos = Insumo.objects.all().order_by('nombre')
    categorias = CategoriaInsumo.objects.all()
    
    alertas_stock = insumos.filter(stock_actual__lte=models.F('stock_minimo')).count()
    
    valor_inventario = 0
    for i in insumos:
        # Ahora multiplicamos Decimal con Decimal, todo compatible
        valor_inventario += (i.stock_actual * i.costo_unitario)

    context = {
        'insumos': insumos,
        'categorias': categorias,
        'alertas_stock': alertas_stock,
        'valor_inventario': valor_inventario,
    }
    return render(request, 'inventory/inventory_list.html', context)

def add_movement(request):
    if request.method == 'POST':
        insumo_id = request.POST.get('insumo_id')
        tipo = request.POST.get('tipo')
        nota = request.POST.get('nota')
        
        # --- FUNCIÓN DE LIMPIEZA (La misma que ya teníamos) ---
        def limpiar_numero(valor):
            if not valor: return Decimal('0.0')
            val_str = str(valor).strip()
            val_str = re.sub(r'[^\d,.-]', '', val_str)
            if ',' in val_str and '.' in val_str:
                if val_str.find(',') > val_str.find('.'):
                    val_str = val_str.replace('.', '').replace(',', '.')
                else:
                    val_str = val_str.replace(',', '')
            elif ',' in val_str:
                val_str = val_str.replace(',', '.')
            try:
                return Decimal(val_str) 
            except:
                return Decimal('0.0')

        # 1. Obtenemos CANTIDAD (Peso) y COSTO TOTAL (Factura)
        cantidad = limpiar_numero(request.POST.get('cantidad'))
        
        # OJO: Este ahora es el precio total que pagaste (ej: $50 por el saco)
        costo_total_factura = limpiar_numero(request.POST.get('costo_total'))

        if cantidad <= 0:
            messages.error(request, "Error: La cantidad debe ser mayor a 0.")
            return redirect('inventory_index')

        insumo = get_object_or_404(Insumo, id=insumo_id)

        # 2. CÁLCULO DEL COSTO UNITARIO (Precio x Kg)
        costo_unitario_calculado = insumo.costo_unitario # Por defecto (si es salida)

        if tipo == 'ENTRADA':
            # Si compré $50 y son 25kg -> 50 / 25 = $2.00 c/u
            if cantidad > 0:
                costo_unitario_calculado = costo_total_factura / cantidad
            else:
                costo_unitario_calculado = Decimal('0.0')

        try:
            MovimientoInventario.objects.create(
                insumo=insumo,
                tipo=tipo,
                cantidad=cantidad,
                # Guardamos el costo unitario ya calculado (la división)
                costo_unitario_movimiento=costo_unitario_calculado,
                usuario=request.user if request.user.is_authenticated else None,
                nota=nota
            )
            messages.success(request, f"Exito: {tipo} registrada.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect('inventory_index')
    
    return redirect('inventory_index')
    """Procesa el formulario usando Decimal para evitar errores de base de datos"""
    if request.method == 'POST':
        insumo_id = request.POST.get('insumo_id')
        tipo = request.POST.get('tipo')
        nota = request.POST.get('nota')
        
        # --- FUNCIÓN DE LIMPIEZA CORREGIDA (Retorna Decimal) ---
        def limpiar_numero(valor):
            if not valor: return Decimal('0.0') # Retornamos Decimal
            
            val_str = str(valor).strip()
            
            # Limpieza de caracteres no numéricos
            val_str = re.sub(r'[^\d,.-]', '', val_str)

            # Lógica de conversión (Punto vs Coma)
            if ',' in val_str and '.' in val_str:
                if val_str.find(',') > val_str.find('.'): # 1.200,50
                    val_str = val_str.replace('.', '').replace(',', '.')
                else: # 1,200.50
                    val_str = val_str.replace(',', '')
            elif ',' in val_str:
                val_str = val_str.replace(',', '.')
            
            try:
                # AQUÍ ESTABA EL ERROR: Antes era float(val_str)
                return Decimal(val_str) 
            except:
                return Decimal('0.0')

        # Procesamos
        cantidad = limpiar_numero(request.POST.get('cantidad'))
        costo = limpiar_numero(request.POST.get('costo'))

        if cantidad <= 0:
            messages.error(request, "Error: La cantidad debe ser mayor a 0.")
            return redirect('inventory_index')

        insumo = get_object_or_404(Insumo, id=insumo_id)

        try:
            MovimientoInventario.objects.create(
                insumo=insumo,
                tipo=tipo,
                cantidad=cantidad,
                # Operador ternario corregido para asegurar Decimales
                costo_unitario_movimiento=costo if tipo == 'ENTRADA' else insumo.costo_unitario,
                usuario=request.user if request.user.is_authenticated else None,
                nota=nota
            )
            messages.success(request, f"Exito: {tipo} registrada correctamente.")
        except Exception as e:
            # Este mensaje te dirá si hay otro error oculto
            messages.error(request, f"Error de Base de Datos: {e}")

        return redirect('inventory_index')
    
    return redirect('inventory_index')

# 1. CREAR INSUMO NUEVO
def insumo_create(request):
    if request.method == 'POST':
        form = InsumoForm(request.POST)
        if form.is_valid():
            insumo = form.save()
            
            # LÓGICA DE FLUJO
            if insumo.es_insumo_compuesto:
                messages.info(request, "Insumo creado. Ahora define su composición.")
                return redirect('insumo_composition', pk=insumo.pk)
            else:
                messages.success(request, "Insumo registrado correctamente.")
                return redirect('inventory_index') # O a donde tengas tu lista
    else:
        form = InsumoForm()

    return render(request, 'inventory/insumo_form.html', {'form': form})

# 2. GESTIONAR COMPOSICIÓN (Para Masa, Salsa, etc.)
# inventory/views.py

@staff_member_required
def insumo_composition(request, pk):
    insumo_padre = get_object_or_404(Insumo, pk=pk)
    
    if not insumo_padre.es_insumo_compuesto:
        messages.error(request, "Este insumo no es compuesto.")
        return redirect('inventory_index')

    if request.method == 'POST':
        # --- LÓGICA DE ELIMINAR/AGREGAR (Se mantiene igual) ---
        if 'delete_componente' in request.POST:
            cid = request.POST.get('delete_componente')
            IngredienteCompuesto.objects.filter(id=cid).delete()
            insumo_padre.calcular_costo_desde_subreceta()
            messages.warning(request, "Ingrediente eliminado.")
            return redirect('insumo_composition', pk=pk)

        form = ComponenteForm(request.POST)
        if form.is_valid():
            comp = form.save(commit=False)
            comp.insumo_padre = insumo_padre
            
            if comp.insumo_hijo == insumo_padre:
                 messages.error(request, "No puedes agregarse a sí mismo.")
            else:
                comp.save()
                insumo_padre.calcular_costo_desde_subreceta()
                messages.success(request, "Ingrediente agregado.")
            return redirect('insumo_composition', pk=pk)
    else:
        form = ComponenteForm()

    # --- NUEVA LÓGICA DE CÁLCULO ---
    componentes = insumo_padre.componentes.select_related('insumo_hijo').all()
    
    total_cantidad_receta = 0
    
    # Recorremos para calcular subtotales precisos en Python
    for comp in componentes:
        # Calculamos el costo exacto (Cantidad * Costo Unitario)
        comp.costo_fila = comp.cantidad * comp.insumo_hijo.costo_unitario
        # Sumamos al peso total
        total_cantidad_receta += comp.cantidad

    context = {
        'insumo': insumo_padre,
        'componentes': componentes,
        'form': form,
        'total_cantidad': total_cantidad_receta, # Enviamos el total a la plantilla
    }
    return render(request, 'inventory/insumo_composition.html', context)

@staff_member_required
def inventory_move(request):
    if request.method == 'POST':
        form = MovimientoInventarioForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            insumo = movimiento.insumo
            
            # VALIDACIÓN DE STOCK NEGATIVO
            # Si intenta sacar más de lo que hay, lanzamos error y no guardamos.
            if movimiento.tipo == 'SALIDA' and movimiento.cantidad > insumo.stock_actual:
                messages.error(request, f"Error: No tienes suficiente stock de {insumo.nombre}. (Actual: {insumo.stock_actual})")
            else:
                movimiento.usuario = request.user
                movimiento.save() # Al guardar, la SEÑAL del modelo actualiza el stock y el precio automáticamente
                
                tipo_accion = "agregada" if movimiento.tipo == 'ENTRADA' else "registrada"
                messages.success(request, f"{movimiento.get_tipo_display()} {tipo_accion} correctamente.")
                return redirect('inventory_index')
    else:
        form = MovimientoInventarioForm()

    return render(request, 'inventory/inventory_move.html', {'form': form})

# inventory/views.py

@staff_member_required
def insumo_edit(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk)
    
    if request.method == 'POST':
        form = InsumoForm(request.POST, instance=insumo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Insumo '{insumo.nombre}' actualizado correctamente.")
            
            # Si es compuesto, preguntamos si quiere ir a editar la receta o volver al inicio
            if insumo.es_insumo_compuesto:
                # Opcional: podrías redirigir a la composición directamente si prefieres
                # return redirect('insumo_composition', pk=insumo.pk)
                pass 

            return redirect('inventory_index')
    else:
        form = InsumoForm(instance=insumo)

    return render(request, 'inventory/insumo_form.html', {
        'form': form, 
        'edit_mode': True, # Bandera para saber que estamos editando
        'insumo': insumo   # Pasamos el objeto para sacar ID y datos extra
    })