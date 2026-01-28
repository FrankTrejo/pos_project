# tables/views.py

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Max
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.template.loader import get_template
from django.db import transaction
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from xhtml2pdf import pisa
from inventory.models import Insumo

# --- IMPORTACIONES DE MODELOS CORRECTAS ---
from .models import (
    Table, Categoria, Producto, TasaBCV, IngredienteProducto, 
    Venta, DetalleVenta, Pago, Orden, DetalleOrden, 
    DetalleOrdenExtra, CostoAdicional, CostoAsignadoProducto, DetalleVentaExtra, PrecioExtra
)
from .forms import (
    ProductoBasicForm, RecetaProductoForm, ProductoPriceForm, 
    CostoAdicionalForm
)
# Importamos modelos de otras apps
from inventory.models import MovimientoInventario, Insumo
from reports.models import AuditoriaEliminacion
from .scrapping import obtener_tasa_bcv

# ==========================================
#  LÓGICA ORIGINAL (MESAS Y POS)
# ==========================================

def initialize_tables_if_empty():
    if Table.objects.count() == 0:
        tables_to_create = []
        for i in range(1, 21):
            tables_to_create.append(Table(number=i))
        Table.objects.bulk_create(tables_to_create)

def index(request):
    initialize_tables_if_empty()
    tables = Table.objects.all()
    return render(request, 'tables/index.html', {'tables': tables})

def create_table(request):
    max_number = Table.objects.aggregate(Max('number'))['number__max']
    new_number = (max_number or 0) + 1
    Table.objects.create(number=new_number)
    return redirect('index')

def toggle_status(request, table_id):
    if request.method == 'POST':
        table = get_object_or_404(Table, id=table_id)
        table.is_occupied = not table.is_occupied
        if not table.is_occupied:
            table.mesero = None
        table.save()
        return JsonResponse({'is_occupied': table.is_occupied})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def asignar_mesero(request, table_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            table = Table.objects.get(id=table_id)
            if user_id:
                user = User.objects.get(id=user_id)
                table.mesero = user
                nombre = user.username
            else:
                table.mesero = None
                nombre = ""
            table.save()
            return JsonResponse({'status': 'ok', 'mesero': nombre})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=400)

def table_order_view(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    
    # 1. Recuperamos la Tasa y Productos
    tasa_actual_texto = obtener_tasa_bcv()
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_numerica = float(tasa_obj.precio) if tasa_obj else 0
    
    categorias = Categoria.objects.all()
    productos = Producto.objects.filter(precio__gt=0).select_related('categoria').order_by('nombre')
    meseros = User.objects.filter(is_active=True, groups__name='Mesero')

    # 2. LOGICA: RECUPERAR EL CARRITO GUARDADO
    orden_activa = Orden.objects.filter(mesa=table).first()
    carrito_recuperado = []
    
    if orden_activa:
        for detalle in orden_activa.detalles.all():
            nombre_display = detalle.producto.nombre
            if detalle.producto.tamano != 'UNI':
                nombre_display += f" ({detalle.producto.tamano})"
            
            # Recuperar Extras
            extras_ids = list(detalle.extras_elegidos.values_list('insumo_id', flat=True))

            carrito_recuperado.append({
                'id': detalle.producto.id,
                'nombre': nombre_display,
                'precio': float(detalle.precio_unitario),
                'cantidad': detalle.cantidad,
                'tamano_codigo': detalle.producto.tamano,
                'para_llevar': detalle.es_para_llevar,
                'extras': extras_ids # <--- ESTO ES VITAL
            })

    carrito_json = json.dumps(carrito_recuperado, cls=DjangoJSONEncoder)
    
    # 3. EXTRAS DISPONIBLES
    lista_extras = Insumo.objects.filter(es_extra=True, stock_actual__gt=0).values(
        'id', 'nombre', 'precio_venta_extra', 'unidad__codigo'
    )
    extras_json = json.dumps(list(lista_extras), cls=DjangoJSONEncoder)
    
    context = {
        'table': table,
        'tasa_cambio': tasa_actual_texto, # Para HTML
        'tasa_valor': tasa_numerica,      # Para JS
        'categorias': categorias,
        'productos': productos,
        'meseros': meseros,
        'orden_activa': orden_activa,
        'carrito_json': carrito_json, 
        'extras_json': extras_json,
    }
    
    return render(request, 'tables/order_detail.html', context)


# ==========================================
#  NUEVA LÓGICA (PRODUCTOS Y RECETAS)
# ==========================================

@staff_member_required
def product_list(request):
    # Usamos prefetch_related para traer los datos relacionados en una sola consulta
    # 'costos_adicionales' es necesario para calcular el Costo Total
    productos = Producto.objects.all().prefetch_related(
        'ingredientes__insumo', 
        'costos_adicionales'
    ).order_by('nombre')
    
    return render(request, 'products/product_list.html', {'productos': productos})

@staff_member_required
def product_create(request, pk=None):
    if pk:
        producto = get_object_or_404(Producto, pk=pk)
        titulo = "Editar Datos Básicos"
    else:
        producto = None
        titulo = "Paso 1: Crear Producto"

    if request.method == 'POST':
        form = ProductoBasicForm(request.POST, instance=producto)
        if form.is_valid():
            prod = form.save(commit=False)
            if not pk:
                prod.precio = 0 
            prod.save()
            messages.success(request, "Datos básicos guardados.")
            return redirect('recipe_manager', pk=prod.pk)
    else:
        form = ProductoBasicForm(instance=producto)

    return render(request, 'products/product_form.html', {'form': form, 'titulo': titulo})

@staff_member_required
def recipe_manager(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        if 'delete_ingrediente' in request.POST:
            ing_id = request.POST.get('delete_ingrediente')
            IngredienteProducto.objects.filter(id=ing_id).delete()
            messages.warning(request, "Ingrediente eliminado.")
            return redirect('recipe_manager', pk=pk)
            
        form = RecetaProductoForm(request.POST)
        if form.is_valid():
            ingrediente = form.save(commit=False)
            ingrediente.producto = producto
            ingrediente.save()
            messages.success(request, "Ingrediente agregado.")
            return redirect('recipe_manager', pk=pk)
    else:
        form = RecetaProductoForm()

    context = {
        'producto': producto,
        'ingredientes': producto.ingredientes.all(),
        'form': form,
        'costo_total': producto.costo_receta,
    }
    return render(request, 'products/recipe_manager.html', context)

@staff_member_required
def product_pricing(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        
        # A) Eliminar un costo
        if 'delete_costo' in request.POST:
            cid = request.POST.get('delete_costo')
            CostoAsignadoProducto.objects.filter(id=cid).delete()
            messages.warning(request, "Costo adicional eliminado.")
            return redirect('product_pricing', pk=pk)
        
        # B) Agregar un costo nuevo
        if 'add_costo' in request.POST:
            datos_formulario = request.POST.copy()
            valor_sucio = datos_formulario.get('valor_aplicado', '')
            if ',' in valor_sucio:
                datos_formulario['valor_aplicado'] = valor_sucio.replace('.', '').replace(',', '.')
            
            form_costo = CostoAdicionalForm(datos_formulario)
            if form_costo.is_valid():
                nuevo_costo = form_costo.save(commit=False)
                nuevo_costo.producto = producto
                nuevo_costo.save()
                messages.success(request, "Costo adicional agregado correctamente.")
                return redirect('product_pricing', pk=pk)
            else:
                messages.error(request, f"Error al agregar costo: {form_costo.errors}")

        # C) Guardar Precio Final
        if 'save_price' in request.POST:
            datos_precio = request.POST.copy()
            precio_sucio = datos_precio.get('precio', '')
            if ',' in precio_sucio:
                 datos_precio['precio'] = precio_sucio.replace('.', '').replace(',', '.')
            
            form_precio = ProductoPriceForm(datos_precio, instance=producto)
            if form_precio.is_valid():
                form_precio.save()
                messages.success(request, f"¡Producto '{producto.nombre}' configurado exitosamente!")
                return redirect('product_list')
            else:
                 messages.error(request, f"Error en el precio: {form_precio.errors}")
    
    form_precio = ProductoPriceForm(instance=producto)
    form_costo = CostoAdicionalForm()

    context = {
        'producto': producto,
        'form_precio': form_precio,
        'form_costo': form_costo,
        'costo_receta': producto.costo_receta,
        'costos_adicionales': producto.costos_adicionales.all(),
        'total_indirectos': producto.costo_indirectos_total,
        'costo_total_final': producto.costo_total_real,
    }
    return render(request, 'products/product_pricing.html', context)

@staff_member_required
def product_delete(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f"Producto '{nombre}' eliminado correctamente.")
    return redirect('product_list')

# ==========================================
#  FUNCIONES AJAX (GUARDADO Y FACTURACIÓN)
# ==========================================

def grabar_mesa_ajax(request, table_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('carrito', [])
            mesero_nombre = data.get('mesero', '')
            
            table = Table.objects.get(id=table_id)
            
            mesero_obj = None
            if mesero_nombre:
                mesero_obj = User.objects.filter(username=mesero_nombre).first()

            # 1. Crear/Recuperar Orden
            orden, created = Orden.objects.get_or_create(mesa=table)
            orden.mesero = mesero_obj
            orden.save()
            
            # 2. BORRÓN Y CUENTA NUEVA
            orden.detalles.all().delete()
            
            # 3. Guardar nuevos items
            for item in items:
                prod_id = item.get('id')
                cant = item.get('cantidad')
                precio = item.get('precio')
                
                prod_obj = Producto.objects.get(id=prod_id)
                
                # A) Detalle Principal
                nuevo_detalle = DetalleOrden.objects.create(
                    orden=orden,
                    producto=prod_obj,
                    cantidad=cant,
                    precio_unitario=precio,
                    es_para_llevar=item.get('para_llevar', False)
                )

                # B) GUARDAR EXTRAS
                ids_extras = item.get('extras', [])
                if ids_extras:
                    for extra_id in ids_extras:
                        try:
                            insumo = Insumo.objects.get(id=extra_id)
                            DetalleOrdenExtra.objects.create(
                                detalle_orden=nuevo_detalle,
                                insumo=insumo,
                                precio=insumo.precio_venta_extra
                            )
                        except Insumo.DoesNotExist:
                            print(f"Error: Insumo ID {extra_id} no existe.")
                        except Exception as e_extra:
                            print(f"Error guardando extra: {e_extra}")

            # 4. Actualizar Mesa
            table.is_occupied = True
            table.mesero = mesero_obj
            table.save()
            
            return JsonResponse({'status': 'ok', 'orden_id': orden.id})
            
        except Exception as e:
            print(f"ERROR GRABAR MESA: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=400)


def generar_ticket_pdf(request, orden_id):
    orden = get_object_or_404(Orden, id=orden_id)
    context = {
        'orden': orden,
        'detalles': orden.detalles.all(),
        'fecha': timezone.now(),
        'total': orden.total_calculado
    }
    
    template_path = 'tables/ticket_pdf.html' 
    template = get_template(template_path)
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="comanda_cocina_mesa_{orden.mesa.number}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    return response

def eliminar_mesa_ajax(request, table_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            motivo = data.get('motivo', 'Sin motivo especificado')
            
            table = get_object_or_404(Table, id=table_id)
            orden = Orden.objects.filter(mesa=table).first()

            if orden:
                detalles_texto = ""
                total_calc = 0
                for det in orden.detalles.all():
                    subt = det.cantidad * det.precio_unitario
                    total_calc += float(subt)
                    detalles_texto += f"{det.cantidad}x {det.producto.nombre} (${subt:.2f})\n"

                AuditoriaEliminacion.objects.create(
                    usuario_responsable=request.user if request.user.is_authenticated else None,
                    mesa_numero=table.number,
                    mesero_asignado=orden.mesero.username if orden.mesero else "Sin Asignar",
                    resumen_pedido=detalles_texto,
                    total_eliminado=total_calc,
                    motivo=motivo
                )
                orden.delete()
            
            table.is_occupied = False
            table.mesero = None
            table.save()
            return JsonResponse({'status': 'ok'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=400)

# tables/views.py

def generar_cuenta_pdf(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    orden = Orden.objects.filter(mesa=table).first()
    
    if not orden:
        return HttpResponse("No hay orden activa para esta mesa", status=404)

    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_valor = float(tasa_obj.precio) if tasa_obj else 0

    # Marcamos solicitud de pago
    table.solicitud_pago = True
    table.save()

    detalles_con_conversion = []
    
    # IMPORTANTE: Inicializamos el Gran Total en 0 para recalcularlo correctamente
    total_acumulado_usd = 0 

    for item in orden.detalles.all():
        # 1. Calcular cuánto suman los extras de ESTA pizza
        # Accedemos a la relación 'extras_elegidos' del modelo
        costo_extras = sum(float(extra.precio) for extra in item.extras_elegidos.all())
        
        # 2. Precio Real Unitario = Precio Pizza + Precio Extras
        precio_unitario_real = float(item.precio_unitario) + costo_extras
        
        # 3. Subtotal Real = (Precio Real) * Cantidad
        subtotal_linea_usd = precio_unitario_real * item.cantidad
        
        # 4. Sumamos al Gran Total de la cuenta
        total_acumulado_usd += subtotal_linea_usd
        
        # Conversión a Bolívares de la línea
        subtotal_linea_bs = subtotal_linea_usd * tasa_valor

        detalles_con_conversion.append({
            'cantidad': item.cantidad,
            'producto': item.producto.nombre,
            'tamano': item.producto.get_tamano_display(),
            
            # Enviamos el precio base original para mostrar "REF BASE"
            'precio_usd': item.precio_unitario, 
            
            # Enviamos el SUBTOTAL CORREGIDO (con extras) para la columna derecha
            'subtotal_usd': subtotal_linea_usd, 
            'subtotal_bs': subtotal_linea_bs,
            'extras_elegidos': item.extras_elegidos.all() 
        })

    # Calculamos el total en Bs basado en el nuevo total USD
    total_acumulado_bs = total_acumulado_usd * tasa_valor

    context = {
        'orden': orden,
        'detalles': detalles_con_conversion,
        'fecha': timezone.now(),
        'tasa': tasa_valor,
        
        # Usamos los totales recalculados
        'total_usd': total_acumulado_usd, 
        'total_bs': total_acumulado_bs
    }

    template_path = 'tables/cuenta_pdf.html'
    template = get_template(template_path)
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="cuenta_mesa_{table.number}.pdf"'
    
    # Corrección para evitar error de tamaño
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    return response
    table = get_object_or_404(Table, id=table_id)
    orden = Orden.objects.filter(mesa=table).first()
    
    if not orden:
        return HttpResponse("No hay orden activa para esta mesa", status=404)

    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_valor = float(tasa_obj.precio) if tasa_obj else 0

    table.solicitud_pago = True
    table.save()

    detalles_con_conversion = []
    total_usd = orden.total_calculado
    total_bs = float(total_usd) * tasa_valor

    for item in orden.detalles.all():
        subtotal_bs = float(item.subtotal) * tasa_valor
        detalles_con_conversion.append({
            'cantidad': item.cantidad,
            'producto': item.producto.nombre,
            'tamano': item.producto.get_tamano_display(),
            'precio_usd': item.precio_unitario,
            'subtotal_usd': item.subtotal,
            'subtotal_bs': subtotal_bs,
            # Pasamos el objeto original para acceder a extras en el template
            'extras_elegidos': item.extras_elegidos.all() 
        })

    context = {
        'orden': orden,
        'detalles': detalles_con_conversion, # Usamos la lista procesada
        'fecha': timezone.now(),
        'tasa': tasa_valor,
        'total_usd': total_usd,
        'total_bs': total_bs
    }

    template_path = 'tables/cuenta_pdf.html'
    template = get_template(template_path)
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="cuenta_mesa_{table.number}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    return response

@staff_member_required
def facturar_mesa_ajax(request, table_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            lista_pagos = data.get('lista_pagos', []) 
            monto_total_recibido = float(data.get('monto_recibido_total', 0))
            es_propina = data.get('es_propina', False)
            
            table = get_object_or_404(Table, id=table_id)
            orden = Orden.objects.filter(mesa=table).first()
            
            if not orden:
                return JsonResponse({'status': 'error', 'message': 'No hay orden.'})

            # --- 1. RECALCULAR TOTALES REALES (Base + Extras) ---
            # No confiamos solo en el total guardado, lo recalculamos para estar seguros
            total_venta_real = 0
            for det in orden.detalles.all():
                precio_base = float(det.precio_unitario)
                costo_extras = sum(float(e.precio) for e in det.extras_elegidos.all())
                subtotal_linea = (precio_base + costo_extras) * det.cantidad
                total_venta_real += subtotal_linea
            
            # Ajustamos la diferencia y propina con el nuevo total real
            diferencia = monto_total_recibido - total_venta_real
            propina_calc = diferencia if (diferencia > 0 and es_propina) else 0

            # --- 2. VALIDACIÓN DE STOCK (Intacta) ---
            insumos_requeridos = {} 
            for detalle in orden.detalles.all():
                # Ingredientes
                for ing in detalle.producto.ingredientes.all():
                    total_item = ing.cantidad * detalle.cantidad
                    if ing.insumo.id in insumos_requeridos: insumos_requeridos[ing.insumo.id] += total_item
                    else: insumos_requeridos[ing.insumo.id] = total_item
                # Extras
                for extra in detalle.extras_elegidos.all():
                    cant_extra = extra.insumo.cantidad_porcion_extra 
                    if cant_extra > 0:
                        if extra.insumo.id in insumos_requeridos: insumos_requeridos[extra.insumo.id] += cant_extra
                        else: insumos_requeridos[extra.insumo.id] = cant_extra

            faltantes = []
            for i_id, cant in insumos_requeridos.items():
                ins_obj = Insumo.objects.get(id=i_id)
                if ins_obj.stock_actual < cant:
                    faltantes.append(f"❌ {ins_obj.nombre}: Stock {ins_obj.stock_actual:.2f} / Req {cant:.2f}")

            if faltantes:
                return JsonResponse({'status': 'error', 'message': "STOCK INSUFICIENTE:\n" + "\n".join(faltantes)})

            # --- 3. TRANSACCIÓN DE GUARDADO ---
            with transaction.atomic():
                # Numeración
                ultima = Venta.objects.last()
                nuevo_num = (int(ultima.codigo_factura) + 1) if (ultima and ultima.codigo_factura.isdigit()) else 1
                codigo = f"{nuevo_num:06d}"

                metodo_general = 'MIXTO' if len(lista_pagos) > 1 else lista_pagos[0]['metodo']
                
                # Crear Venta con el TOTAL REAL RECALCULADO
                venta = Venta.objects.create(
                    codigo_factura=codigo,
                    total=total_venta_real, # <--- USAMOS EL RECALCULADO
                    metodo_pago=metodo_general,
                    mesero=orden.mesero,
                    mesa_numero=table.number,
                    monto_recibido=monto_total_recibido,
                    propina=propina_calc
                )

                # Registrar Pagos
                for p in lista_pagos:
                    Pago.objects.create(venta=venta, metodo=p['metodo'], monto=p['monto'])

                # Procesar Detalles
                for det in orden.detalles.all():
                    # Calculamos subtotal individual para este item
                    precio_base = float(det.precio_unitario)
                    costo_extras = sum(float(e.precio) for e in det.extras_elegidos.all())
                    subtotal_real = (precio_base + costo_extras) * det.cantidad

                    # Crear DetalleVenta
                    dv = DetalleVenta.objects.create(
                        venta=venta, 
                        producto=det.producto, 
                        nombre_producto=det.producto.nombre,
                        cantidad=det.cantidad, 
                        precio_unitario=det.precio_unitario, # Precio base visual
                        subtotal=subtotal_real # Subtotal con extras incluidos
                    )
                    
                    # === AQUÍ GUARDAMOS LOS EXTRAS EN EL HISTÓRICO ===
                    for extra_orden in det.extras_elegidos.all():
                        DetalleVentaExtra.objects.create(
                            detalle_venta=dv,
                            nombre_extra=extra_orden.insumo.nombre,
                            precio=extra_orden.precio
                        )
                    # =================================================

                    # Descuento Inventario (Receta)
                    for ing in det.producto.ingredientes.all():
                        MovimientoInventario.objects.create(
                            insumo=ing.insumo, tipo='SALIDA', cantidad=ing.cantidad * det.cantidad,
                            unidad_movimiento=ing.insumo.unidad, usuario=request.user,
                            nota=f"Fac: {codigo} - {det.producto.nombre}"
                        )
                    
                    # Descuento Inventario (Extras)
                    for extra in det.extras_elegidos.all():
                        if extra.insumo.cantidad_porcion_extra > 0:
                            MovimientoInventario.objects.create(
                                insumo=extra.insumo, tipo='SALIDA', 
                                cantidad=extra.insumo.cantidad_porcion_extra,
                                unidad_movimiento=extra.insumo.unidad, usuario=request.user,
                                nota=f"Fac: {codigo} - Extra {extra.insumo.nombre}"
                            )

                # Descuento de Cajas (Empaques)
                for det in orden.detalles.all():
                    if det.es_para_llevar:
                        MAPA_CAJAS = {'IND': 'CAJA INDIVIDUAL', 'MED': 'CAJA MEDIANA', 'FAM': 'CAJA FAMILIAR'}
                        nombre_caja = MAPA_CAJAS.get(det.producto.tamano)
                        if nombre_caja:
                            caja_insumo = Insumo.objects.filter(nombre__iexact=nombre_caja).first()
                            if caja_insumo:
                                MovimientoInventario.objects.create(
                                    insumo=caja_insumo, tipo='SALIDA', cantidad=det.cantidad,
                                    unidad_movimiento=caja_insumo.unidad, usuario=request.user,
                                    nota=f"Empaque Fac: {codigo}"
                                )

                orden.delete()
                table.is_occupied = False
                table.solicitud_pago = False
                table.mesero = None
                table.save()

            return JsonResponse({'status': 'ok', 'venta_id': venta.id})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=400)

@staff_member_required
def generar_factura_pdf(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_valor = float(tasa_obj.precio) if tasa_obj else 0
    total_bs = float(venta.total) * tasa_valor

    context = {
        'venta': venta,
        'detalles': venta.detalles.all(),
        'tasa': tasa_valor,
        'total_bs': total_bs,
        'vuelto': float(venta.monto_recibido) - float(venta.total) - float(venta.propina)
    }
    
    template_path = 'tables/factura_final_pdf.html'
    template = get_template(template_path)
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename="Factura_{venta.codigo_factura}.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    return response

def anular_venta(request, venta_id):
    if request.method == 'POST':
        venta = get_object_or_404(Venta, id=venta_id)
        motivo = request.POST.get('motivo', 'Sin motivo especificado')
        if venta.anulada:
            messages.error(request, "Esta venta ya estaba anulada.")
            return redirect('reporte_ventas') 

        try:
            with transaction.atomic():
                for detalle in venta.detalles.all():
                    producto = detalle.producto
                    cantidad_vendida = detalle.cantidad
                    if producto:
                        # Reponer receta base
                        for ingrediente in producto.ingredientes.all():
                            MovimientoInventario.objects.create(
                                insumo=ingrediente.insumo, tipo='ENTRADA',
                                cantidad=ingrediente.cantidad * cantidad_vendida,
                                usuario=request.user,
                                nota=f"ANULACIÓN Venta #{venta.codigo_factura}: {producto.nombre}",
                                costo_unitario_movimiento=ingrediente.insumo.costo_unitario 
                            )
                        # Nota: Reponer extras sería ideal si los guardaras en historial
                        
                venta.anulada = True
                venta.motivo_anulacion = motivo
                venta.fecha_anulacion = timezone.now()
                venta.usuario_anulacion = request.user
                venta.save()
                messages.success(request, f"Venta #{venta.codigo_factura} anulada.")

        except Exception as e:
            messages.error(request, f"Error al anular: {e}")

    return redirect('reporte_ventas_detalle')

@staff_member_required
def gestion_precios_extras(request):
    insumos = Insumo.objects.filter(es_extra=True).order_by('nombre')
    tamanos = ['IND', 'MED', 'FAM'] 

    if request.method == 'POST':
        try:
            # Iteramos sobre los datos recibidos
            for key, value in request.POST.items():
                
                # CASO 1: Guardar PRECIO (name="precio_ID_TAM")
                if key.startswith('precio_'):
                    parts = key.split('_')
                    insumo_id = parts[1]
                    tamano_code = parts[2]
                    
                    # Convertimos vacío a 0
                    val_precio = value if value else 0
                    
                    # Buscamos o creamos el registro y actualizamos SOLO el precio
                    obj, created = PrecioExtra.objects.get_or_create(
                        insumo_id=insumo_id,
                        tamano=tamano_code
                    )
                    obj.precio = val_precio
                    obj.save()

                # CASO 2: Guardar CANTIDAD/PESO (name="cantidad_ID_TAM")
                elif key.startswith('cantidad_'):
                    parts = key.split('_')
                    insumo_id = parts[1]
                    tamano_code = parts[2]
                    
                    val_cantidad = value if value else 0
                    
                    obj, created = PrecioExtra.objects.get_or_create(
                        insumo_id=insumo_id,
                        tamano=tamano_code
                    )
                    obj.cantidad = val_cantidad
                    obj.save()

            messages.success(request, "Precios y porciones actualizados correctamente.")
            return redirect('manage_extras')
            
        except Exception as e:
            messages.error(request, f"Error al guardar: {str(e)}")

    # Preparamos los datos para pintar en el HTML
    precios_data = PrecioExtra.objects.all()
    diccionario_datos = {}
    
    for p in precios_data:
        diccionario_datos[f"precio_{p.insumo.id}_{p.tamano}"] = p.precio
        diccionario_datos[f"cantidad_{p.insumo.id}_{p.tamano}"] = p.cantidad

    # === TRUCO PARA QUE EL TEMPLATE FUNCIONE BIEN ===
    # Agregamos un atributo temporal 'id_str' a cada insumo
    # Esto ayuda a que el filtro de búsqueda en el HTML no se rompa
    for insumo in insumos:
        insumo.id_str = str(insumo.id)

    return render(request, 'products/manage_extras.html', {
        'insumos': insumos,
        'tamanos': tamanos,
        'datos': diccionario_datos
    })