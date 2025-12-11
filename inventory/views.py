from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Insumo, MovimientoInventario, CategoriaInsumo
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