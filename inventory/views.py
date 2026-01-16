from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Insumo, MovimientoInventario, CategoriaInsumo, IngredienteCompuesto, ConsumoInterno
from .forms import InsumoForm, ComponenteForm, MovimientoInventarioForm
from django.db import models
import re
from decimal import Decimal  # <--- IMPORTANTE: Importamos el tipo de dato correcto
from django.db.models import ProtectedError 
from django.db import transaction # Importante para que no descuente uno si falla el otro
from .forms import ProduccionForm
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponseRedirect, HttpResponse

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
        
        try:
            unidades = Decimal(request.POST.get('cantidad_unidades', '0'))
        except:
            unidades = 0
            
        insumo = get_object_or_404(Insumo, id=insumo_id)

        # --- CORRECCIÓN AQUÍ ---
        # Antes bloqueábamos si era <= 0. 
        # Ahora: Si es AJUSTE, permitimos negativos. Si es ENTRADA/SALIDA, exigimos positivos.
        
        if tipo != 'AJUSTE' and unidades <= 0:
            messages.error(request, "Para Entradas y Salidas la cantidad debe ser mayor a 0.")
            return redirect('inventory_index')
            
        if tipo == 'AJUSTE' and unidades == 0:
             messages.error(request, "El ajuste no puede ser 0.")
             return redirect('inventory_index')

        # Calculamos gramos reales (manteniendo el signo si es negativo)
        peso_por_unidad = insumo.peso_standar 
        cantidad_real_gramos = unidades * peso_por_unidad
        
        # Costo (Solo informativo)
        costo_total_movimiento = abs(unidades * insumo.precio_mercado)

        try:
            MovimientoInventario.objects.create(
                insumo=insumo,
                tipo=tipo,
                cantidad=cantidad_real_gramos, 
                usuario=request.user if request.user.is_authenticated else None,
                nota=f"{nota} (Carga: {unidades} Unds)",
                costo_unitario_movimiento=costo_total_movimiento 
            )
            messages.success(request, f"Movimiento registrado correctamente.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect('inventory_index')
    
    return redirect('inventory_index')
    if request.method == 'POST':
        insumo_id = request.POST.get('insumo_id')
        tipo = request.POST.get('tipo')
        nota = request.POST.get('nota')
        
        # SOLO RECIBIMOS LAS UNIDADES (Cajas, Sacos, Botellas)
        try:
            unidades = Decimal(request.POST.get('cantidad_unidades', '0'))
        except:
            unidades = 0
            
        insumo = get_object_or_404(Insumo, id=insumo_id)

        if unidades <= 0:
            messages.error(request, "La cantidad debe ser mayor a 0.")
            return redirect('inventory_index')

        # 1. BUSCAMOS EL PESO EN EL MAESTRO (Base de Datos)
        # Ya no se lo pedimos al usuario.
        peso_por_unidad = insumo.peso_standar 
        
        # Calculamos cuántos gramos reales están entrando
        cantidad_real_gramos = unidades * peso_por_unidad

        # 2. BUSCAMOS EL COSTO EN EL MAESTRO (Base de Datos)
        costo_total_movimiento = unidades * insumo.precio_mercado

        # Validación de seguridad: Si el producto no tiene peso configurado en el maestro
        if peso_por_unidad <= 0:
            messages.warning(request, f"⚠️ El producto '{insumo.nombre}' no tiene peso configurado en el Maestro. Se cargó en 0.")

        try:
            MovimientoInventario.objects.create(
                insumo=insumo,
                tipo=tipo,
                cantidad=cantidad_real_gramos, # Guardamos gramos para el stock
                usuario=request.user if request.user.is_authenticated else None,
                nota=f"{nota} (Carga: {unidades} Unds x {peso_por_unidad} {insumo.unidad.codigo})",
                costo_unitario_movimiento=costo_total_movimiento 
            )
            messages.success(request, f"¡Éxito! Se procesaron {unidades} unidades. Stock aumentado en {cantidad_real_gramos} {insumo.unidad.codigo}.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Insumo, IngredienteCompuesto

def insumo_composition(request, insumo_id):
    insumo_padre = get_object_or_404(Insumo, id=insumo_id)
    
    # 1. AGREGAR INGREDIENTE (Lógica POST se mantiene igual)
    if request.method == 'POST' and 'add_ingredient' in request.POST:
        hijo_id = request.POST.get('insumo_hijo')
        cantidad = request.POST.get('cantidad')
        
        if hijo_id and cantidad:
            try:
                insumo_hijo = Insumo.objects.get(id=hijo_id)
                IngredienteCompuesto.objects.create(
                    insumo_padre=insumo_padre,
                    insumo_hijo=insumo_hijo,
                    cantidad=cantidad
                )
                # FORZAMOS RE-CALCULO INMEDIATO
                insumo_padre.calcular_costo_desde_subreceta()
                messages.success(request, f"Agregado: {insumo_hijo.nombre}")
            except Exception as e:
                messages.error(request, f"Error al agregar: {e}")
        
        return redirect('insumo_composition', insumo_id=insumo_id)

    # 2. ELIMINAR INGREDIENTE (Lógica POST se mantiene igual)
    if request.method == 'POST' and 'delete_ingredient' in request.POST:
        ingrediente_id = request.POST.get('ingrediente_id')
        try:
            item = IngredienteCompuesto.objects.get(id=ingrediente_id)
            nombre = item.insumo_hijo.nombre
            item.delete()
            # FORZAMOS RE-CALCULO INMEDIATO
            insumo_padre.calcular_costo_desde_subreceta()
            messages.success(request, f"Eliminado: {nombre}")
        except:
            messages.error(request, "Error al eliminar.")
        return redirect('insumo_composition', insumo_id=insumo_id)

    # 3. PREPARAR DATOS PARA LA VISTA (AQUÍ ESTÁ EL CAMBIO)
    
    # Insumos disponibles para el selector
    insumos_disponibles = Insumo.objects.filter(es_insumo_compuesto=False).exclude(id=insumo_id).order_by('nombre')
    
    # Traemos los ingredientes actuales de la base de datos
    # Usamos select_related para optimizar la consulta del costo unitario del hijo
    raw_ingredientes = insumo_padre.componentes.select_related('insumo_hijo').all()

    # --- CÁLCULO PRECISO EN PYTHON ---
    ingredientes_procesados = []
    costo_total_lote = 0

    for comp in raw_ingredientes:
        # Calculamos el subtotal exacto con decimales (Cantidad * Costo Unitario)
        subtotal = comp.cantidad * comp.insumo_hijo.costo_unitario
        
        # Le "pegamos" este valor calculado al objeto ingrediente temporalmente
        comp.subtotal_calculado = subtotal
        
        # Sumamos al total acumulado
        costo_total_lote += subtotal
        
        # Agregamos a la lista nueva
        ingredientes_procesados.append(comp)

    return render(request, 'inventory/insumo_composition.html', {
        'insumo': insumo_padre,
        'insumos_disponibles': insumos_disponibles,
        'ingredientes': ingredientes_procesados, # Pasamos la lista procesada con los costos
        'costo_total_lote': costo_total_lote
    })
    insumo_padre = get_object_or_404(Insumo, id=insumo_id)
    
    # 1. AGREGAR INGREDIENTE
    if request.method == 'POST' and 'add_ingredient' in request.POST:
        hijo_id = request.POST.get('insumo_hijo')
        cantidad = request.POST.get('cantidad')
        
        if hijo_id and cantidad:
            try:
                insumo_hijo = Insumo.objects.get(id=hijo_id)
                IngredienteCompuesto.objects.create(
                    insumo_padre=insumo_padre,
                    insumo_hijo=insumo_hijo,
                    cantidad=cantidad
                )
                # FORZAMOS RE-CALCULO INMEDIATO
                insumo_padre.calcular_costo_desde_subreceta()
                messages.success(request, f"Agregado: {insumo_hijo.nombre}")
            except Exception as e:
                messages.error(request, f"Error al agregar: {e}")

        
        return redirect('insumo_composition', insumo_id=insumo_id)

    # 2. ELIMINAR INGREDIENTE
    if request.method == 'POST' and 'delete_ingredient' in request.POST:
        ingrediente_id = request.POST.get('ingrediente_id')
        try:
            item = IngredienteCompuesto.objects.get(id=ingrediente_id)
            nombre = item.insumo_hijo.nombre
            item.delete()
            # FORZAMOS RE-CALCULO INMEDIATO
            insumo_padre.calcular_costo_desde_subreceta()
            messages.success(request, f"Eliminado: {nombre}")
        except:
            messages.error(request, "Error al eliminar.")
        return redirect('insumo_composition', insumo_id=insumo_id)

    # 3. LISTAR (EXCLUYENDO AL PROPIO PADRE PARA EVITAR BUCLES INFINITOS)
    # Mostramos todos los insumos disponibles para agregar, menos él mismo.
    insumos_disponibles = Insumo.objects.filter(es_insumo_compuesto=False).exclude(id=insumo_id).order_by('nombre')
    
    # Si quieres permitir agregar OTRAS recetas dentro de esta receta (Sub-recetas), 
    # quita el "es_insumo_compuesto=False" del filtro de arriba.

    ingredientes = insumo_padre.componentes.all()

    # --- NUEVO CÁLCULO PARA MOSTRAR ---
    # Sumamos (Cantidad * Costo) de cada ingrediente
    costo_total_lote = sum(comp.cantidad * comp.insumo_hijo.costo_unitario for comp in ingredientes)

    return render(request, 'inventory/insumo_composition.html', {
        'insumo': insumo_padre,
        'insumos_disponibles': insumos_disponibles,
        'ingredientes': ingredientes,
        'costo_total_lote': costo_total_lote  # <--- ¡NO OLVIDES AGREGAR ESTO AQUÍ!
    })

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

@staff_member_required
def insumo_delete(request, pk):
    insumo = get_object_or_404(Insumo, pk=pk)
    
    if request.method == 'POST':
        try:
            nombre = insumo.nombre
            insumo.delete()
            messages.success(request, f"El insumo '{nombre}' y su historial han sido eliminados.")
        except ProtectedError:
            messages.error(request, f"No se puede eliminar '{insumo.nombre}' porque se está usando en una Receta (Insumo Compuesto). Elimínalo de la receta primero.")
        except Exception as e:
            messages.error(request, f"Ocurrió un error al eliminar: {e}")
            
    return redirect('inventory_index')



from django.db import transaction # IMPORTANTE: Agrega esto arriba
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal
from .models import Insumo, MovimientoInventario

@staff_member_required
# inventory/views.py

def insumo_produccion(request, pk):
    insumo_padre = get_object_or_404(Insumo, pk=pk)
    ingredientes = insumo_padre.componentes.all()

    if request.method == 'POST':
        try:
            # AHORA RECIBIMOS LOTES (Ej: 1, 2, 0.5)
            lotes = Decimal(request.POST.get('cantidad_lotes', '1'))
        except:
            lotes = 0
            
        if lotes <= 0:
            messages.error(request, "La cantidad de lotes debe ser mayor a 0.")
            return redirect('insumo_produccion', pk=pk)

        # 1. CALCULAMOS LA CANTIDAD FINAL A SUMAR AL STOCK
        # Si el rendimiento base es 2700g y hago 2 lotes -> 5400g
        rendimiento_base = insumo_padre.rendimiento
        cantidad_total_producir = lotes * rendimiento_base

        # 2. EL FACTOR DE MULTIPLICACIÓN ES SIMPLEMENTE LA CANTIDAD DE LOTES
        # Si la receta está configurada para 1 lote, y hago 2, multiplico ingredientes por 2.
        factor = lotes

        try:
            with transaction.atomic():
                # A. VERIFICAR STOCK
                errores_stock = []
                for componente in ingredientes:
                    cantidad_necesaria = componente.cantidad * factor
                    if componente.insumo_hijo.stock_actual < cantidad_necesaria:
                        errores_stock.append(f"Falta {componente.insumo_hijo.nombre} (Tienes {componente.insumo_hijo.stock_actual:g}, necesitas {cantidad_necesaria:g})")
                
                if errores_stock:
                    for error in errores_stock:
                        messages.error(request, error)
                    return redirect('insumo_produccion', pk=pk)

                # B. DESCONTAR INGREDIENTES
                for componente in ingredientes:
                    cantidad_a_descontar = componente.cantidad * factor
                    
                    MovimientoInventario.objects.create(
                        insumo=componente.insumo_hijo,
                        tipo='SALIDA',
                        cantidad=cantidad_a_descontar,
                        usuario=request.user,
                        nota=f"Producción: {lotes} Lotes de {insumo_padre.nombre}"
                    )

                # C. SUMAR PRODUCTO TERMINADO
                MovimientoInventario.objects.create(
                    insumo=insumo_padre,
                    tipo='ENTRADA',
                    cantidad=cantidad_total_producir,
                    usuario=request.user,
                    # El costo unitario se mantiene, multiplicamos por la cantidad total producida
                    costo_unitario_movimiento=insumo_padre.costo_unitario * cantidad_total_producir, 
                    nota=f"Producción Finalizada ({lotes} Lotes)"
                )
                
                messages.success(request, f"¡Listo! Se cocinaron {lotes} lotes ({cantidad_total_producir:g} {insumo_padre.unidad.codigo}).")
                return redirect('inventory_index')

        except Exception as e:
            messages.error(request, f"Error: {e}")
            return redirect('insumo_produccion', pk=pk)

    return render(request, 'inventory/insumo_produccion.html', {
        'insumo': insumo_padre,
        'ingredientes': ingredientes
    })
    # Buscamos el producto "padre" (La Salsa, la Masa, etc.)
    insumo_padre = get_object_or_404(Insumo, pk=pk)
    
    # Obtenemos sus ingredientes
    ingredientes = insumo_padre.componentes.all()

    if request.method == 'POST':
        try:
            cantidad_a_producir = Decimal(request.POST.get('cantidad_producir', '0'))
        except:
            cantidad_a_producir = 0
            
        if cantidad_a_producir <= 0:
            messages.error(request, "Debes ingresar una cantidad mayor a 0.")
            return redirect('insumo_produccion', pk=pk)

        # VALIDACIÓN DE SEGURIDAD
        rendimiento_base = insumo_padre.rendimiento
        if rendimiento_base <= 0:
            rendimiento_base = 1 # Evitar división por cero si no configuraste rendimiento

        # Factor de Escala: Si la receta es para 1kg y hago 5kg, el factor es 5.
        factor = cantidad_a_producir / rendimiento_base

        # INICIO DE LA TRANSACCIÓN (Todo o Nada)
        try:
            with transaction.atomic():
                
                # 1. VERIFICAR STOCK SUFICIENTE
                errores_stock = []
                for componente in ingredientes:
                    cantidad_necesaria = componente.cantidad * factor
                    if componente.insumo_hijo.stock_actual < cantidad_necesaria:
                        errores_stock.append(f"Falta {componente.insumo_hijo.nombre} (Tienes {componente.insumo_hijo.stock_actual}, necesitas {cantidad_necesaria})")
                
                if errores_stock:
                    # Si falta algo, detenemos todo y avisamos
                    for error in errores_stock:
                        messages.error(request, error)
                    return redirect('insumo_produccion', pk=pk)

                # 2. DESCONTAR INGREDIENTES (SALIDA)
                for componente in ingredientes:
                    cantidad_a_descontar = componente.cantidad * factor
                    
                    MovimientoInventario.objects.create(
                        insumo=componente.insumo_hijo,
                        tipo='SALIDA',
                        cantidad=cantidad_a_descontar,
                        usuario=request.user,
                        nota=f"Producción de {cantidad_a_producir} {insumo_padre.unidad.codigo} de {insumo_padre.nombre}"
                    )

                # 3. SUMAR PRODUCTO TERMINADO (ENTRADA)
                MovimientoInventario.objects.create(
                    insumo=insumo_padre,
                    tipo='ENTRADA',
                    cantidad=cantidad_a_producir,
                    usuario=request.user,
                    # El costo ya viene calculado en el insumo padre, pero aquí podríamos recalcularlo si quisiéramos
                    costo_unitario_movimiento=insumo_padre.costo_unitario * cantidad_a_producir, 
                    nota=f"Producción interna (Lote cocinado)"
                )
                
                messages.success(request, f"¡Éxito! Se produjeron {cantidad_a_producir} {insumo_padre.unidad.codigo} de {insumo_padre.nombre}. Ingredientes descontados.")
                return redirect('inventory_index')

        except Exception as e:
            messages.error(request, f"Ocurrió un error inesperado: {e}")
            return redirect('insumo_produccion', pk=pk)

    return render(request, 'inventory/insumo_produccion.html', {
        'insumo': insumo_padre,
        'ingredientes': ingredientes
    })
    insumo_padre = get_object_or_404(Insumo, pk=pk)
    
    # Validaciones básicas
    if not insumo_padre.es_insumo_compuesto:
        messages.error(request, "Solo se pueden producir insumos con receta.")
        return redirect('inventory_index')

    componentes = insumo_padre.componentes.select_related('insumo_hijo').all()
    if not componentes:
        messages.warning(request, "Define la receta primero.")
        return redirect('insumo_composition', pk=pk)

    # 1. CALCULAR PESO DE 1 LOTE (Suma de todos los ingredientes)
    # Ej: 10000 Harina + 4000 Agua = 14000 Gramos por Lote
    peso_por_lote = sum(comp.cantidad for comp in componentes)

    if request.method == 'POST':
        form = ProduccionForm(request.POST)
        if form.is_valid():
            lotes = form.cleaned_data['cantidad_lotes'] # Número entero (1, 2, 3...)
            nota = form.cleaned_data['nota']

            # 2. VALIDAR STOCK (Multiplicación simple)
            alcanza = True
            msg_error = ""
            
            for comp in componentes:
                # Si receta dice 14g y hago 1 lote -> necesito 14g. Exacto.
                necesario = comp.cantidad * lotes
                
                if comp.insumo_hijo.stock_actual < necesario:
                    alcanza = False
                    msg_error = f"Falta {comp.insumo_hijo.nombre}. Tienes {comp.insumo_hijo.stock_actual:.0f}, necesitas {necesario:.0f}."
                    break
            
            if not alcanza:
                messages.error(request, f"⛔ No alcanza el inventario: {msg_error}")
            else:
                try:
                    with transaction.atomic():
                        # A) RESTAR INGREDIENTES
                        for comp in componentes:
                            cantidad_descontar = comp.cantidad * lotes
                            
                            MovimientoInventario.objects.create(
                                insumo=comp.insumo_hijo,
                                tipo='SALIDA',
                                cantidad=cantidad_descontar,
                                unidad_movimiento=comp.insumo_hijo.unidad,
                                usuario=request.user,
                                nota=f"Prod. {lotes} lote(s) de {insumo_padre.nombre}"
                            )

                        # B) SUMAR PRODUCTO TERMINADO (Peso del lote * lotes)
                        cantidad_producida = peso_por_lote * lotes
                        
                        MovimientoInventario.objects.create(
                            insumo=insumo_padre,
                            tipo='ENTRADA',
                            cantidad=cantidad_producida,
                            unidad_movimiento=insumo_padre.unidad,
                            # El costo unitario se mantiene
                            costo_unitario_movimiento=insumo_padre.costo_unitario * cantidad_producida,
                            usuario=request.user,
                            nota=f"Producción {lotes} lote(s). {nota}"
                        )
                    
                    messages.success(request, f"¡Listo! Se agregaron {cantidad_producida:.0f}g de {insumo_padre.nombre} (x{lotes} Lotes).")
                    return redirect('inventory_index')

                except Exception as e:
                    messages.error(request, f"Error: {e}")

    else:
        form = ProduccionForm()

    return render(request, 'inventory/produccion_form.html', {
        'form': form,
        'insumo': insumo_padre,
        'componentes': componentes,
        'peso_lote': peso_por_lote
    })
    insumo_padre = get_object_or_404(Insumo, pk=pk)
    
    if not insumo_padre.es_insumo_compuesto:
        messages.error(request, "Solo se pueden producir insumos compuestos (Recetas).")
        return redirect('inventory_index')

    # Obtenemos la receta (componentes)
    componentes = insumo_padre.componentes.all()
    if not componentes:
        messages.warning(request, "Este insumo no tiene receta definida. Ve a 'Ingeniería de Receta' primero.")
        return redirect('insumo_composition', pk=pk)

    if request.method == 'POST':
        form = ProduccionForm(request.POST)
        if form.is_valid():
            cantidad_producir = form.cleaned_data['cantidad_a_producir'] # Ej: 10000 gramos
            nota = form.cleaned_data['nota']

            # 1. VALIDACIÓN DE STOCK (¿Me alcanza la harina?)
            alcanza = True
            msg_error = ""
            
            # Simulamos el consumo para ver si alcanza
            for comp in componentes:
                # La receta dice cuánto necesito para 1 unidad (1 gramo de masa)
                # Multiplicamos por lo que quiero producir
                # Ej: 0.6g Harina * 10000g Masa = 6000g Harina necesaria
                necesario = comp.cantidad * cantidad_producir
                
                if comp.insumo_hijo.stock_actual < necesario:
                    alcanza = False
                    msg_error = f"Falta stock de {comp.insumo_hijo.nombre}. Tienes {comp.insumo_hijo.stock_actual:.2f}, necesitas {necesario:.2f}."
                    break
            
            if not alcanza:
                messages.error(request, f"No se puede producir: {msg_error}")
            else:
                # 2. EJECUCIÓN (Usamos transaction para que sea todo o nada)
                try:
                    with transaction.atomic():
                        # A) RESTAR INGREDIENTES (Salidas)
                        for comp in componentes:
                            cantidad_descontar = comp.cantidad * cantidad_producir
                            MovimientoInventario.objects.create(
                                insumo=comp.insumo_hijo,
                                tipo='SALIDA',
                                cantidad=cantidad_descontar,
                                # Asumimos que la cantidad ya está en la unidad base (Gramos)
                                # Si tuvieras 'unidad_movimiento', habría que buscar la unidad 'Gramos'
                                # Para simplificar, dejamos unidad_movimiento en None (Factor 1) o buscamos la unidad base.
                                unidad_movimiento=comp.insumo_hijo.unidad, 
                                usuario=request.user,
                                nota=f"Prod. {insumo_padre.nombre} (ID: {insumo_padre.id})"
                            )

                        # B) SUMAR PRODUCTO TERMINADO (Entrada)
                        MovimientoInventario.objects.create(
                            insumo=insumo_padre,
                            tipo='ENTRADA',
                            cantidad=cantidad_producir,
                            unidad_movimiento=insumo_padre.unidad,
                            costo_unitario_movimiento=insumo_padre.costo_unitario * cantidad_producir, # Valor total
                            usuario=request.user,
                            nota=f"Producción Interna. {nota}"
                        )
                    
                    messages.success(request, f"¡Producción exitosa! Se han creado {cantidad_producir} {insumo_padre.unidad.codigo} de {insumo_padre.nombre}.")
                    return redirect('inventory_index')

                except Exception as e:
                    messages.error(request, f"Error en base de datos: {e}")

    else:
        form = ProduccionForm()

    return render(request, 'inventory/produccion_form.html', {
        'form': form,
        'insumo': insumo_padre,
        'componentes': componentes
    })

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Insumo, MovimientoInventario, ConsumoInterno
from tables.models import Producto
from django.db import transaction

# CONFIGURACIÓN: Define qué insumos conforman la "BASE" de la comida de personal
# Pon aquí los IDs o Nombres de: Masa, Salsa, Queso.
# Ejemplo: Supongamos que Masa es ID 1, Salsa ID 2, Queso ID 3.
# Ajusta las cantidades según tu receta de personal (ej: 250g masa, 100g queso...)
BASE_PERSONAL = [
    {'insumo_id': 1, 'cantidad': 250}, # Masa
    {'insumo_id': 2, 'cantidad': 100}, # Salsa
    {'insumo_id': 3, 'cantidad': 150}, # Queso
]

# inventory/views.py

def salidas_especiales_view(request):
    # 1. Traer datos para el formulario
    productos = Producto.objects.all().order_by('nombre')
    # Traemos todos los insumos simples para los extras
    ingredientes_extra = Insumo.objects.filter(es_insumo_compuesto=False).order_by('nombre')
    
    # Historial reciente
    historial = ConsumoInterno.objects.all().order_by('-fecha')[:20]

    if request.method == 'POST':
        tipo_accion = request.POST.get('tipo_accion')
        nota = request.POST.get('nota', '')

        try:
            with transaction.atomic():
                costo_total = 0

                # ==========================================
                # CASO 1: COMIDA DE PERSONAL (LÓGICA AVANZADA)
                # ==========================================
                if tipo_accion == 'PERSONAL':
                    tamano = request.POST.get('tamano_pizza') # 'IND', 'MED', 'FAM'
                    empleado = request.POST.get('empleado_nombre')

                    # A) BUSCAR LA RECETA BASE (La Margarita del tamaño elegido)
                    producto_base = Producto.objects.filter(nombre__icontains='MARGARITA', tamano=tamano).first()

                    if not producto_base:
                        messages.error(request, f"Error: No existe una 'Pizza Margarita' tamaño {tamano} para usar de base.")
                        return redirect('salidas_especiales')

                    registro = ConsumoInterno.objects.create(
                        tipo='PERSONAL',
                        usuario=request.user,
                        descripcion=f"Personal: {empleado} ({producto_base.nombre} {producto_base.get_tamano_display()})"
                    )

                    # B) DESCONTAR LA BASE (Según receta de Margarita)
                    for componente in producto_base.ingredientes.all():
                        MovimientoInventario.objects.create(
                            insumo=componente.insumo,
                            tipo='SALIDA',
                            cantidad=componente.cantidad,
                            unidad_movimiento=componente.insumo.unidad,
                            usuario=request.user,
                            nota=f"Base Personal #{registro.id}"
                        )
                        costo_total += (componente.insumo.costo_unitario * componente.cantidad)

                    # C) DESCONTAR LOS EXTRAS (Cantidades exactas)
                    ids_extras = request.POST.getlist('extra_id')
                    cantidades_extras = request.POST.getlist('extra_cantidad')

                    for i, insumo_id in enumerate(ids_extras):
                        cantidad_texto = cantidades_extras[i]
                        
                        # Validamos que no venga vacío y sea mayor a 0
                        if cantidad_texto and float(cantidad_texto) > 0:
                            cantidad = Decimal(cantidad_texto) # <--- AQUÍ CORREGIMOS EL ERROR DE DECIMAL
                            
                            insumo = Insumo.objects.get(id=insumo_id)
                            
                            MovimientoInventario.objects.create(
                                insumo=insumo,
                                tipo='SALIDA',
                                cantidad=cantidad,
                                unidad_movimiento=insumo.unidad,
                                usuario=request.user,
                                nota=f"Extra Personal #{registro.id}"
                            )
                            # Calculamos costo (Decimal * Decimal)
                            costo_total += (insumo.costo_unitario * cantidad)

                # ==========================================
                # CASO 2: REGALO / CORTESÍA
                # ==========================================
                elif tipo_accion == 'REGALO':
                    prod_id = request.POST.get('producto_regalo')
                    prod_obj = Producto.objects.get(id=prod_id)
                    
                    registro = ConsumoInterno.objects.create(
                        tipo='CORTESIA',
                        usuario=request.user,
                        descripcion=f"Regalo: {prod_obj.nombre} - {nota}"
                    )

                    for ing in prod_obj.ingredientes.all():
                        MovimientoInventario.objects.create(
                            insumo=ing.insumo, tipo='SALIDA', cantidad=ing.cantidad,
                            unidad_movimiento=ing.insumo.unidad, usuario=request.user,
                            nota=f"Regalo #{registro.id}"
                        )
                        costo_total += (ing.insumo.costo_unitario * ing.cantidad)

                # Guardamos costo final
                registro.costo_estimado = costo_total
                registro.save()
                
                # --- CORRECCIÓN DEFINITIVA ---
                messages.success(request, f"Salida registrada exitosamente.")
                
                # Importamos aquí mismo para evitar el error de variable local
                from django.urls import reverse 
                
                base_url = reverse('salidas_especiales')
                final_url = f"{base_url}?print_id={registro.id}"
                
                return HttpResponseRedirect(final_url)

        except Exception as e:
            messages.error(request, f"Error técnico: {str(e)}")
            return redirect('salidas_especiales')

    return render(request, 'inventory/salidas_especiales.html', {
        'productos': productos,
        'ingredientes': ingredientes_extra,
        'historial': historial
    })
    # 1. Traer datos para el formulario
    productos = Producto.objects.all().order_by('nombre')
    # Traemos todos los insumos simples para los extras
    ingredientes_extra = Insumo.objects.filter(es_insumo_compuesto=False).order_by('nombre')
    
    # Historial reciente
    historial = ConsumoInterno.objects.all().order_by('-fecha')[:20]

    if request.method == 'POST':
        tipo_accion = request.POST.get('tipo_accion')
        nota = request.POST.get('nota', '')

        try:
            with transaction.atomic():
                costo_total = 0

                # ==========================================
                # CASO 1: COMIDA DE PERSONAL (AVANZADO)
                # ==========================================
                if tipo_accion == 'PERSONAL':
                    tamano = request.POST.get('tamano_pizza') # 'IND', 'MED', 'FAM'
                    empleado = request.POST.get('empleado_nombre')

                    # A) BUSCAR LA RECETA BASE (La Margarita del tamaño elegido)
                    # Buscamos un producto que se llame "Margarita" y tenga el tamaño correcto
                    producto_base = Producto.objects.filter(nombre__icontains='MARGARITA', tamano=tamano).first()

                    if not producto_base:
                        messages.error(request, f"Error: No existe una 'Pizza Margarita' tamaño {tamano} para usar de base.")
                        return redirect('salidas_especiales')

                    registro = ConsumoInterno.objects.create(
                        tipo='PERSONAL',
                        usuario=request.user,
                        descripcion=f"Personal: {empleado} ({producto_base.nombre} {producto_base.get_tamano_display()})"
                    )

                    # B) DESCONTAR LA BASE (Según receta de Margarita)
                    for componente in producto_base.ingredientes.all():
                        MovimientoInventario.objects.create(
                            insumo=componente.insumo,
                            tipo='SALIDA',
                            cantidad=componente.cantidad, # Cantidad exacta de la receta
                            unidad_movimiento=componente.insumo.unidad,
                            usuario=request.user,
                            nota=f"Base Personal #{registro.id}"
                        )
                        costo_total += (componente.insumo.costo_unitario * componente.cantidad)

                    # C) DESCONTAR LOS EXTRAS (Cantidades exactas)
                    # Recibimos listas paralelas de IDs y Cantidades
                    ids_extras = request.POST.getlist('extra_id')
                    cantidades_extras = request.POST.getlist('extra_cantidad')

                    for i, insumo_id in enumerate(ids_extras):
                        # ERROR ANTERIOR: cantidad = float(cantidades_extras[i])
                        # CORRECCIÓN: Usamos Decimal para que sea compatible con el dinero
                        cantidad_texto = cantidades_extras[i]
                        
                        # Validamos que no venga vacío para que no de error
                        if cantidad_texto and float(cantidad_texto) > 0:
                            cantidad = Decimal(cantidad_texto) # <--- AQUÍ ESTÁ LA MAGIA
                            
                            insumo = Insumo.objects.get(id=insumo_id)
                            
                            MovimientoInventario.objects.create(
                                insumo=insumo,
                                tipo='SALIDA',
                                cantidad=cantidad,
                                unidad_movimiento=insumo.unidad,
                                usuario=request.user,
                                nota=f"Extra Personal #{registro.id}"
                            )
                            # Ahora sí: Decimal * Decimal = Éxito
                            costo_total += (insumo.costo_unitario * cantidad)


                # ==========================================
                # CASO 2: REGALO / CORTESÍA (IGUAL QUE ANTES)
                # ==========================================
                elif tipo_accion == 'REGALO':
                    prod_id = request.POST.get('producto_regalo')
                    prod_obj = Producto.objects.get(id=prod_id)
                    
                    registro = ConsumoInterno.objects.create(
                        tipo='CORTESIA',
                        usuario=request.user,
                        descripcion=f"Regalo: {prod_obj.nombre} - {nota}"
                    )

                    for ing in prod_obj.ingredientes.all():
                        MovimientoInventario.objects.create(
                            insumo=ing.insumo, tipo='SALIDA', cantidad=ing.cantidad,
                            unidad_movimiento=ing.insumo.unidad, usuario=request.user,
                            nota=f"Regalo #{registro.id}"
                        )
                        costo_total += (ing.insumo.costo_unitario * ing.cantidad)

                # Guardamos costo final
                registro.costo_estimado = costo_total
                registro.save()
                
                messages.success(request, f"Salida registrada exitosamente.")
                
                # CAMBIO CLAVE: Redirigimos pasando el ID para imprimir
                from django.urls import reverse

                # Construimos la URL con el parámetro ?print_id=123
                url_base = reverse('salidas_especiales')
                url_destino = f"{url_base}?print_id={registro.id}"
                
                return redirect(url_destino)

        except Exception as e:
            messages.error(request, f"Error técnico: {str(e)}")

    return render(request, 'inventory/salidas_especiales.html', {
        'productos': productos,
        'ingredientes': ingredientes_extra,
        'historial': historial
    })
    # Obtenemos productos para el select de "Regalos"
    productos = Producto.objects.all()
    # Obtenemos insumos (ingredientes) para que el personal elija sus extras
    # Filtramos solo insumos que sean ingredientes (no cajas, servilletas, etc)
    # Ajusta el filtro según tu categoría de ingredientes
    ingredientes_extra = Insumo.objects.filter(es_insumo_compuesto=False).order_by('nombre')

    if request.method == 'POST':
        tipo_accion = request.POST.get('tipo_accion') # 'PERSONAL' o 'REGALO'
        nota = request.POST.get('nota', '')

        try:
            with transaction.atomic():
                costo_total_operacion = 0
                
                # --- CASO 1: COMIDA DE PERSONAL ---
                if tipo_accion == 'PERSONAL':
                    # 1. Recuperar los 2 ingredientes extra seleccionados
                    extras_ids = request.POST.getlist('extras') # Lista de IDs
                    
                    if len(extras_ids) > 2:
                        messages.error(request, "Solo se permiten 2 ingredientes extra.")
                        return redirect('salidas_especiales')

                    registro = ConsumoInterno.objects.create(
                        tipo='PERSONAL',
                        usuario=request.user,
                        descripcion=f"Comida Personal: {nota}"
                    )

                    # A) Descontar la BASE (Masa, Salsa, Queso)
                    for item in BASE_PERSONAL:
                        try:
                            insumo = Insumo.objects.get(id=item['insumo_id'])
                            MovimientoInventario.objects.create(
                                insumo=insumo,
                                tipo='SALIDA',
                                cantidad=item['cantidad'],
                                unidad_movimiento=insumo.unidad,
                                usuario=request.user,
                                nota=f"Personal #{registro.id}"
                            )
                            costo_total_operacion += (insumo.costo_unitario * item['cantidad'])
                        except Insumo.DoesNotExist:
                            pass # Manejar si no existe el ID configurado

                    # B) Descontar los EXTRAS seleccionados
                    # Asumiremos una cantidad estándar para el extra (ej: 50g de jamón)
                    CANTIDAD_EXTRA_ESTANDAR = 50 
                    
                    for extra_id in extras_ids:
                        insumo_extra = Insumo.objects.get(id=extra_id)
                        MovimientoInventario.objects.create(
                            insumo=insumo_extra,
                            tipo='SALIDA',
                            cantidad=CANTIDAD_EXTRA_ESTANDAR,
                            unidad_movimiento=insumo_extra.unidad,
                            usuario=request.user,
                            nota=f"Extra Personal #{registro.id}"
                        )
                        costo_total_operacion += (insumo_extra.costo_unitario * CANTIDAD_EXTRA_ESTANDAR)


                # --- CASO 2: REGALO / CORTESÍA ---
                elif tipo_accion == 'REGALO':
                    producto_id = request.POST.get('producto_regalo')
                    producto = Producto.objects.get(id=producto_id)
                    
                    registro = ConsumoInterno.objects.create(
                        tipo='CORTESIA',
                        usuario=request.user,
                        descripcion=f"Regalo: {producto.nombre} - {nota}"
                    )

                    # Descontar receta del producto
                    ingredientes = producto.ingredientes.all()
                    for ing in ingredientes:
                        MovimientoInventario.objects.create(
                            insumo=ing.insumo,
                            tipo='SALIDA',
                            cantidad=ing.cantidad,
                            unidad_movimiento=ing.insumo.unidad,
                            usuario=request.user,
                            nota=f"Regalo #{registro.id}"
                        )
                        # Calculamos costo
                        costo_total_operacion += (ing.insumo.costo_unitario * ing.cantidad)

                # Guardamos el costo final
                registro.costo_estimado = costo_total_operacion
                registro.save()
                
                messages.success(request, "Salida registrada e inventario actualizado.")
                return redirect('salidas_especiales')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return render(request, 'inventory/salidas_especiales.html', {
        'productos': productos,
        'ingredientes': ingredientes_extra
    })

    # --- AGREGAR ESTO AL FINAL ---
    # Recuperamos los últimos 20 registros para mostrarlos en la tabla
    historial = ConsumoInterno.objects.all().order_by('-fecha')[:20]

    return render(request, 'inventory/salidas_especiales.html', {
        'productos': productos,
        'ingredientes': ingredientes_extra,
        'historial': historial # <--- Enviamos esto al HTML
    })

from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse

def generar_comanda_interno_pdf(request, consumo_id):
    consumo = get_object_or_404(ConsumoInterno, id=consumo_id)
    
    # Lógica para limpiar el texto
    # Si dice: "Personal: Manuel (MARGARITA INDIVIDUAL)" -> Nos quedamos con "Personal: Manuel"
    descripcion_limpia = consumo.descripcion.split('(')[0].strip()
    
    context = {
        'consumo': consumo,
        'fecha': consumo.fecha,
        'extras': [],
        'titulo_principal': descripcion_limpia  # <--- Enviamos el nombre limpio
    }

    if consumo.tipo == 'PERSONAL':
        movimientos_extra = MovimientoInventario.objects.filter(
            nota=f"Extra Personal #{consumo.id}"
        )
        context['extras'] = movimientos_extra
    
    # (El resto de la función sigue igual...)
    template_path = 'inventory/comanda_interno_pdf.html'
    template = get_template(template_path)
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="comanda_interna_{consumo.id}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    
    return response

from .forms import RecetaInsumoForm # Importa el formulario nuevo

# Vista exclusiva para crear RECETAS en Inventario
def receta_create(request):
    if request.method == 'POST':
        form = RecetaInsumoForm(request.POST) # Usa el form ligero
        if form.is_valid():
            insumo = form.save()
            # ---> ESTA LÍNEA ES LA CLAVE <---
            # Debe llevarte a 'insumo_composition' pasando el ID
            return redirect('insumo_composition', insumo_id=insumo.id)
            
    else:
        form = RecetaInsumoForm()
    
    return render(request, 'inventory/receta_form.html', {'form': form})