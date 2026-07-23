# tables/views.py

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Max
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.template.loader import get_template
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from django.db.models.functions import Cast
from django.db.models import IntegerField
from django.core.serializers.json import DjangoJSONEncoder
from xhtml2pdf import pisa
from inventory.models import Insumo
from core.models import Configuracion
from .utils_impresora import mandar_a_tickera, imprimir_comanda, imprimir_precuenta

# --- IMPORTACIONES DE MODELOS CORRECTAS ---
from .models import (
    Table, Categoria, Producto, TasaBCV, IngredienteProducto, 
    Venta, DetalleVenta, Pago, Orden, DetalleOrden, 
    DetalleOrdenExtra, CostoAdicional, CostoAsignadoProducto, DetalleVentaExtra, PrecioExtra,
    DetalleOrdenRemovido, DetalleVentaRemovido
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
    # Actualizamos la tasa al cargar el mapa de mesas (inicio del POS)
    obtener_tasa_bcv()
    
    # --- LÓGICA CORREGIDA: SEPARAMOS LAS MESAS ---
    internal_tables = Table.objects.filter(is_external=False).order_by(Cast('number', output_field=IntegerField()))
    external_tables = Table.objects.filter(is_external=True).order_by(Cast('number', output_field=IntegerField()))

    # --- LÓGICA CORREGIDA PARA CALCULAR SIGUIENTES NÚMEROS EN SUS RANGOS ---
    # Siguiente para mesas INTERNAS (rango 1-100)
    internal_numbers = [int(n) for n in internal_tables.values_list('number', flat=True) if n.isdigit()]
    next_internal_number = max(internal_numbers) + 1 if internal_numbers else 1
    if next_internal_number > 100: next_internal_number = None # No se pueden crear más

    # Siguiente para mesas EXTERNAS (rango 101-200)
    external_numbers_db = [int(n) for n in external_tables.values_list('number', flat=True) if n.isdigit()]
    next_external_number = max(external_numbers_db) + 1 if external_numbers_db else 101
    if next_external_number < 101: next_external_number = 101 # Asegura que empiece en 101
    if next_external_number > 200: next_external_number = None # No se pueden crear más

    return render(request, 'tables/index.html', {
        'internal_tables': internal_tables, 
        'external_tables': external_tables,
        'next_internal_number': next_internal_number, 
        'next_external_number': next_external_number
    })

def create_table(request):
    if request.method == 'POST':
        is_external = request.POST.get('is_external') == 'on'        
        
        if is_external:
            # Lógica para mesas externas (rango 101-200)
            name = request.POST.get('name')
            color = request.POST.get('color')
            external_numbers = [int(n) for n in Table.objects.filter(is_external=True).values_list('number', flat=True) if n.isdigit()]
            new_number = max(external_numbers) + 1 if external_numbers else 101
            if new_number < 101: new_number = 101
            if new_number > 200:
                messages.error(request, "No se pueden crear más mesas externas (límite 200 alcanzado).")
                return redirect('index')
            Table.objects.create(number=new_number, name=name, color=color, is_external=True)
        else:
            # Lógica para mesas internas (rango 1-100)
            internal_numbers = [int(n) for n in Table.objects.filter(is_external=False).values_list('number', flat=True) if n.isdigit()]
            max_int_num = max(internal_numbers) if internal_numbers else 0
            new_number = max_int_num + 1
            if new_number > 100:
                messages.error(request, "No se pueden crear más mesas internas (límite 100 alcanzado).")
                return redirect('index')
            Table.objects.create(number=new_number, is_external=False)

        messages.success(request, f"Mesa #{new_number} creada exitosamente.")
        return redirect('index')

    # La lógica GET ahora está en la vista 'index' que renderiza el modal

    # Para GET, pre-calculamos el siguiente número de mesa
    max_number = Table.objects.aggregate(Max('number'))['number__max'] or 0
    next_number = max_number + 1
    
    return render(request, 'tables/create_table.html', {
        'next_number': next_number
    })

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
    
    config = Configuracion.get_solo()
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_bcv_real = float(tasa_obj.precio) if tasa_obj else 0
    
    # 1. Tasa Global del Sistema
    if config.usar_scraping_bcv:
        tasa_numerica = tasa_bcv_real
        tasa_actual_texto = f"{tasa_numerica:.2f} Bs/S" if tasa_bcv_real else "0.00 Bs/S"
    else:
        tasa_numerica = float(config.tasa_dolar)
        tasa_actual_texto = f"{tasa_numerica:.2f} Bs/S (Manual)"
    
    # 2. Tasa Específica de Cashea
    if config.usar_tasa_bcv_para_cashea:
        tasa_cashea_valor = tasa_bcv_real
    else:
        if config.tasa_cashea > 0:
            tasa_cashea_valor = float(config.tasa_cashea)
        else:
            tasa_cashea_valor = tasa_numerica # fallback

    
    categorias = Categoria.objects.all()
    productos = Producto.objects.filter(precio__gt=0).select_related('categoria').order_by('id')
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
            extras_list = []
            for extra in detalle.extras_elegidos.all():
                extras_list.append({
                    'id': extra.insumo_id,
                    'porcion': float(extra.porcion),
                    'es_sustituto': float(extra.precio) == 0.0
                })
            
            mitad_id = detalle.mitad_producto.id if detalle.mitad_producto else None
            mitad_nombre = detalle.mitad_producto.nombre if detalle.mitad_producto else None
            
            removidos = []
            removidos_nombres = []
            for rem in detalle.ingredientes_removidos.all():
                removidos.append({'id': rem.id, 'porcion': 1.0})
                removidos_nombres.append(rem.nombre)
                
            if hasattr(detalle, 'removidos_detalles'):
                for rem in detalle.removidos_detalles.all():
                    removidos.append({'id': rem.insumo.id, 'porcion': float(rem.porcion)})
                    porcion_str = "1/4 " if rem.porcion == Decimal('0.25') else "1/2 " if rem.porcion == Decimal('0.50') else "3/4 " if rem.porcion == Decimal('0.75') else ""
                    removidos_nombres.append(f"{porcion_str}{rem.insumo.nombre}")
            
            cuarto_2_id = detalle.cuarto_2_producto.id if detalle.cuarto_2_producto else None
            cuarto_2_nombre = detalle.cuarto_2_producto.nombre if detalle.cuarto_2_producto else None
            cuarto_3_id = detalle.cuarto_3_producto.id if detalle.cuarto_3_producto else None
            cuarto_3_nombre = detalle.cuarto_3_producto.nombre if detalle.cuarto_3_producto else None
            cuarto_4_id = detalle.cuarto_4_producto.id if detalle.cuarto_4_producto else None
            cuarto_4_nombre = detalle.cuarto_4_producto.nombre if detalle.cuarto_4_producto else None

            carrito_recuperado.append({
                'id': detalle.producto.id,
                'nombre': nombre_display,
                'precio': float(detalle.precio_unitario),
                'cantidad': detalle.cantidad,
                'tamano_codigo': detalle.producto.tamano,
                'para_llevar': detalle.es_para_llevar,
                'extras': extras_list,
                'mitad_id': mitad_id,
                'mitad_nombre': mitad_nombre,
                'cuarto_2_id': cuarto_2_id,
                'cuarto_2_nombre': cuarto_2_nombre,
                'cuarto_3_id': cuarto_3_id,
                'cuarto_3_nombre': cuarto_3_nombre,
                'cuarto_4_id': cuarto_4_id,
                'cuarto_4_nombre': cuarto_4_nombre,
                'removidos': removidos,
                'removidos_nombres': removidos_nombres,
                'es_nuevo': not detalle.impreso
            })

    carrito_json = json.dumps(carrito_recuperado, cls=DjangoJSONEncoder)
    
    ingredientes_por_producto = {}
    productos_lista = []
    for p in productos:
        ingredientes_por_producto[p.id] = [
            {'id': ing.insumo.id, 'nombre': ing.insumo.nombre} 
            for ing in p.ingredientes.all()
        ]
        productos_lista.append({
            'id': p.id, 'nombre': p.nombre, 'tamano': p.tamano, 'precio': float(p.precio)
        })
    
    ingredientes_dict_json = json.dumps(ingredientes_por_producto)
    productos_json = json.dumps(productos_lista)
    
    # 3. EXTRAS DISPONIBLES
    # MODIFICADO: Traemos los precios específicos por tamaño
    insumos_extras = Insumo.objects.filter(es_extra=True, stock_actual__gt=0).prefetch_related('precios_extra')
    lista_extras_procesada = []
    
    for insumo in insumos_extras:
        # Convertimos la relación inversa a un diccionario { 'IND': 1.50, 'MED': 2.00 }
        precios_dict = {pe.tamano: float(pe.precio) for pe in insumo.precios_extra.all()}
        
        lista_extras_procesada.append({
            'id': insumo.id,
            'nombre': insumo.nombre,
            'precio_venta_extra': float(insumo.precio_venta_extra), # Precio base por si acaso
            'unidad__codigo': insumo.unidad.codigo,
            'precios_por_tamano': precios_dict 
        })

    extras_json = json.dumps(lista_extras_procesada, cls=DjangoJSONEncoder)
    
    context = {
        'table': table,
        'tasa_cambio': tasa_actual_texto, # Para HTML
        'tasa_valor': tasa_numerica,      # Para JS
        'tasa_cashea_valor': tasa_cashea_valor, # Para JS
        'categorias': categorias,
        'productos': productos,
        'meseros': meseros,
        'orden_activa': orden_activa,
        'carrito_json': carrito_json, 
        'ingredientes_dict_json': ingredientes_dict_json,
        'productos_json': productos_json,
        'extras_json': extras_json,
    }
    
    return render(request, 'tables/order_detail.html', context)


# ==========================================
#  NUEVA LÓGICA (PRODUCTOS Y RECETAS)
# ==========================================

@staff_member_required
def product_list(request):
    query = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    tamano = request.GET.get('tamano', '')

    # Usamos prefetch_related para traer los datos relacionados en una sola consulta
    # 'costos_adicionales' es necesario para calcular el Costo Total
    productos_list = Producto.objects.all().prefetch_related(
        'ingredientes__insumo', 
        'costos_adicionales'
    ).order_by('id')
    
    if query:
        productos_list = productos_list.filter(nombre__icontains=query)
        
    if categoria_id:
        productos_list = productos_list.filter(categoria_id=categoria_id)
        
    if tamano:
        productos_list = productos_list.filter(tamano=tamano)

    paginator = Paginator(productos_list, 10)
    page_number = request.GET.get('page')
    productos = paginator.get_page(page_number)

    categorias = Categoria.objects.all()
    tamanos = Producto.OPCIONES_TAMANO

    return render(request, 'products/product_list.html', {
        'productos': productos,
        'q': query,
        'categoria_sel': categoria_id,
        'tamano_sel': tamano,
        'categorias': categorias,
        'tamanos': tamanos,
    })

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
            config = Configuracion.get_solo()
            if not pk:
                prod.precio = 0
                prod.save()
                if config.codigo_producto_automatico:
                    prod.codigo = str(prod.id)
            else:
                if config.codigo_producto_automatico and not prod.codigo:
                    prod.codigo = str(prod.id)
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
def bulk_recipe_update(request):
    if request.method == 'POST':
        insumo_id = request.POST.get('insumo_id')
        cantidad_str = request.POST.get('cantidad')
        producto_ids = request.POST.getlist('productos')
        
        if not insumo_id or not cantidad_str or not producto_ids:
            messages.error(request, "Debe seleccionar un ingrediente, una cantidad y al menos un producto de la lista.")
            return redirect('bulk_recipe_update')
            
        try:
            cantidad = Decimal(cantidad_str.replace(',', '.'))
            insumo = get_object_or_404(Insumo, id=insumo_id)
            
            with transaction.atomic():
                for p_id in producto_ids:
                    producto = Producto.objects.get(id=p_id)
                    ing_prod, created = IngredienteProducto.objects.get_or_create(
                        producto=producto,
                        insumo=insumo,
                        defaults={'cantidad': cantidad}
                    )
                    if not created:
                        ing_prod.cantidad = cantidad
                        ing_prod.save()
                    
            messages.success(request, f"¡Éxito! Se actualizó '{insumo.nombre}' a {cantidad} {insumo.unidad.codigo} en {len(producto_ids)} productos.")
            return redirect('product_list')
            
        except Exception as e:
            messages.error(request, f"Error técnico: {e}")
            return redirect('bulk_recipe_update')

    context = {
        'categorias': Categoria.objects.all(),
        'tamanos': Producto.OPCIONES_TAMANO,
        'productos': Producto.objects.all().select_related('categoria').order_by('nombre'),
        'insumos': Insumo.objects.all().order_by('nombre'),
    }
    return render(request, 'products/bulk_recipe_update.html', context)

@staff_member_required
def bulk_cost_update(request):
    if request.method == 'POST':
        accion = request.POST.get('accion', 'aplicar')
        costo_id = request.POST.get('costo_id')
        valor_str = request.POST.get('valor_aplicado')
        producto_ids = request.POST.getlist('productos')
        
        if not costo_id or not producto_ids:
            messages.error(request, "Debe seleccionar un costo adicional y al menos un producto de la lista.")
            return redirect('bulk_cost_update')
            
        if accion == 'aplicar' and not valor_str:
            messages.error(request, "Debe ingresar un valor a aplicar.")
            return redirect('bulk_cost_update')
            
        try:
            costo_adicional = get_object_or_404(CostoAdicional, id=costo_id)
            
            with transaction.atomic():
                if accion == 'eliminar':
                    CostoAsignadoProducto.objects.filter(
                        producto_id__in=producto_ids,
                        costo_adicional=costo_adicional
                    ).delete()
                    messages.success(request, f"¡Éxito! Se ELIMINÓ el costo '{costo_adicional.nombre}' de los {len(producto_ids)} productos seleccionados.")
                else:
                    valor = Decimal(valor_str.replace(',', '.'))
                    agregados = 0
                    omitidos = 0
                    
                    for p_id in producto_ids:
                        producto = Producto.objects.get(id=p_id)
                        
                        # Verificamos si ya existe para no duplicarlo ni sobreescribirlo
                        existe = CostoAsignadoProducto.objects.filter(producto=producto, costo_adicional=costo_adicional).exists()
                        
                        if not existe:
                            CostoAsignadoProducto.objects.create(producto=producto, costo_adicional=costo_adicional, valor_aplicado=valor)
                            agregados += 1
                        else:
                            omitidos += 1
                            
                    mensaje = f"¡Éxito! Se aplicó el costo '{costo_adicional.nombre}' a {agregados} producto(s)."
                    if omitidos > 0:
                        mensaje += f" Se omitieron {omitidos} porque ya lo tenían."
                    messages.success(request, mensaje)

            return redirect('product_list')
            
        except Exception as e:
            messages.error(request, f"Error técnico: {e}")
            return redirect('bulk_cost_update')

    context = {
        'categorias': Categoria.objects.all(),
        'tamanos': Producto.OPCIONES_TAMANO,
        'productos': Producto.objects.all().select_related('categoria').order_by('nombre'),
        'costos_adicionales': CostoAdicional.objects.all().order_by('nombre'),
    }
    return render(request, 'products/bulk_cost_update.html', context)

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

def calcular_insumos_requeridos_json(items):
    insumos_requeridos = {}
    for item in items:
        prod_id = item.get('id')
        cant = Decimal(str(item.get('cantidad', 1)))
        mitad_id = item.get('mitad_id')
        cuarto_2_id = item.get('cuarto_2_id')
        cuarto_3_id = item.get('cuarto_3_id')
        cuarto_4_id = item.get('cuarto_4_id')
        removidos = item.get('removidos', [])
        ids_extras = item.get('extras', [])
        para_llevar = item.get('para_llevar', False)
        
        removidos_dict = {}
        for rem_data in removidos:
            try:
                if isinstance(rem_data, dict):
                    removidos_dict[int(rem_data.get('id', 0))] = Decimal(str(rem_data.get('porcion', 1.0)))
                else:
                    removidos_dict[int(rem_data)] = Decimal('1.0')
            except: pass
                
        prod_obj = Producto.objects.get(id=prod_id)
        
        if cuarto_2_id and cuarto_3_id and cuarto_4_id:
            c2_obj = Producto.objects.get(id=cuarto_2_id)
            c3_obj = Producto.objects.get(id=cuarto_3_id)
            c4_obj = Producto.objects.get(id=cuarto_4_id)
            ings_prod1 = {ing.insumo.id: ing for ing in prod_obj.ingredientes.all()}
            ings_prod2 = {ing.insumo.id: ing for ing in c2_obj.ingredientes.all()}
            ings_prod3 = {ing.insumo.id: ing for ing in c3_obj.ingredientes.all()}
            ings_prod4 = {ing.insumo.id: ing for ing in c4_obj.ingredientes.all()}
            all_i_ids = set(ings_prod1.keys()) | set(ings_prod2.keys()) | set(ings_prod3.keys()) | set(ings_prod4.keys())
            for i_id in all_i_ids:
                porcion_removida = removidos_dict.get(i_id, Decimal('0.0'))
                if porcion_removida >= Decimal('1.0'): continue
                
                cantidades = []
                if i_id in ings_prod1: cantidades.append(ings_prod1[i_id].cantidad)
                if i_id in ings_prod2: cantidades.append(ings_prod2[i_id].cantidad)
                if i_id in ings_prod3: cantidades.append(ings_prod3[i_id].cantidad)
                if i_id in ings_prod4: cantidades.append(ings_prod4[i_id].cantidad)
                
                # Estandarizamos a la porción mínima para evitar excesos si una receta difiere
                qty = min(cantidades) * (Decimal(len(cantidades)) / Decimal('4.0'))
                qty = qty * (Decimal('1.0') - porcion_removida)
                if qty > 0:
                    insumos_requeridos[i_id] = insumos_requeridos.get(i_id, Decimal('0.0')) + (qty * cant)
        elif mitad_id:
            mitad_obj = Producto.objects.get(id=mitad_id)
            ings_prod1 = {ing.insumo.id: ing for ing in prod_obj.ingredientes.all()}
            ings_prod2 = {ing.insumo.id: ing for ing in mitad_obj.ingredientes.all()}
            for i_id in set(ings_prod1.keys()).union(set(ings_prod2.keys())):
                porcion_removida = removidos_dict.get(i_id, Decimal('0.0'))
                if porcion_removida >= Decimal('1.0'): continue
                
                cantidades = []
                if i_id in ings_prod1: cantidades.append(ings_prod1[i_id].cantidad)
                if i_id in ings_prod2: cantidades.append(ings_prod2[i_id].cantidad)
                
                qty = min(cantidades) * (Decimal(len(cantidades)) / Decimal('2.0'))
                qty = qty * (Decimal('1.0') - porcion_removida)
                insumos_requeridos[i_id] = insumos_requeridos.get(i_id, Decimal('0.0')) + (qty * cant)
        else:
            for ing in prod_obj.ingredientes.all():
                porcion_removida = removidos_dict.get(ing.insumo.id, Decimal('0.0'))
                if porcion_removida >= Decimal('1.0'): continue
                
                qty = ing.cantidad * (Decimal('1.0') - porcion_removida)
                if qty > 0:
                    insumos_requeridos[ing.insumo.id] = insumos_requeridos.get(ing.insumo.id, Decimal('0.0')) + (qty * cant)
                    
        if ids_extras:
            for extra_data in ids_extras:
                extra_id = extra_data.get('id') if isinstance(extra_data, dict) else extra_data
                porcion = Decimal(str(extra_data.get('porcion', 1.0))) if isinstance(extra_data, dict) else Decimal('1.0')
                es_sustituto = extra_data.get('es_sustituto', False) if isinstance(extra_data, dict) else False
                try:
                    insumo = Insumo.objects.get(id=extra_id)
                    if es_sustituto:
                        cantidad_a_descontar = porcion
                    else:
                        cantidad_a_descontar = insumo.cantidad_porcion_extra
                        precio_obj = PrecioExtra.objects.filter(insumo=insumo, tamano=prod_obj.tamano).first()
                        if precio_obj and precio_obj.cantidad > 0:
                            cantidad_a_descontar = precio_obj.cantidad
                        cantidad_a_descontar = cantidad_a_descontar * porcion
                        
                    cant_extra = cantidad_a_descontar * cant
                    if cant_extra > 0:
                        insumos_requeridos[insumo.id] = insumos_requeridos.get(insumo.id, Decimal('0.0')) + cant_extra
                except: pass

        if para_llevar:
            config_global = Configuracion.get_solo()
            caja_insumo = None
            if prod_obj.tamano == 'IND': caja_insumo = config_global.caja_individual
            elif prod_obj.tamano == 'MED': caja_insumo = config_global.caja_mediana
            elif prod_obj.tamano == 'FAM': caja_insumo = config_global.caja_familiar
            if caja_insumo:
                insumos_requeridos[caja_insumo.id] = insumos_requeridos.get(caja_insumo.id, Decimal('0.0')) + cant
    return insumos_requeridos

def procesar_inventario_orden(orden, usuario, nota_base, tipo_movimiento):
    for det in orden.detalles.all():
        # --- LÓGICA CORREGIDA PARA MANEJAR REMOVIDOS ---
        removidos_dict = {}
        # Primero, los removidos simples (porción completa)
        if hasattr(det, 'ingredientes_removidos') and det.ingredientes_removidos.exists():
            for r in det.ingredientes_removidos.all():
                removidos_dict[r.id] = Decimal('1.0')
        
        # Luego, los removidos con porción específica (sobrescribe si es necesario)
        if hasattr(det, 'removidos_detalles'):
            for r in det.removidos_detalles.all():
                if r.insumo: # Verificación de seguridad
                    removidos_dict[r.insumo.id] = r.porcion
        # --- FIN DE LA CORRECCIÓN ---

        if getattr(det, 'cuarto_2_producto', None) and getattr(det, 'cuarto_3_producto', None) and getattr(det, 'cuarto_4_producto', None):
            ings_prod1 = {ing.insumo.id: ing for ing in det.producto.ingredientes.all()}
            ings_prod2 = {ing.insumo.id: ing for ing in det.cuarto_2_producto.ingredientes.all()}
            ings_prod3 = {ing.insumo.id: ing for ing in det.cuarto_3_producto.ingredientes.all()}
            ings_prod4 = {ing.insumo.id: ing for ing in det.cuarto_4_producto.ingredientes.all()}
            
            all_i_ids = set(ings_prod1.keys()) | set(ings_prod2.keys()) | set(ings_prod3.keys()) | set(ings_prod4.keys())
            for i_id in all_i_ids:
                porcion_removida = removidos_dict.get(i_id, Decimal('0.0'))
                if porcion_removida >= Decimal('1.0'): continue
                
                cantidades = []
                ins = None
                if i_id in ings_prod1: 
                    cantidades.append(ings_prod1[i_id].cantidad)
                    ins = ings_prod1[i_id].insumo
                if i_id in ings_prod2: 
                    cantidades.append(ings_prod2[i_id].cantidad)
                    if not ins: ins = ings_prod2[i_id].insumo
                if i_id in ings_prod3: 
                    cantidades.append(ings_prod3[i_id].cantidad)
                    if not ins: ins = ings_prod3[i_id].insumo
                if i_id in ings_prod4: 
                    cantidades.append(ings_prod4[i_id].cantidad)
                    if not ins: ins = ings_prod4[i_id].insumo
                
                qty = min(cantidades) * (Decimal(len(cantidades)) / Decimal('4.0'))
                qty = qty * (Decimal('1.0') - porcion_removida)
                if qty > 0 and ins:
                    MovimientoInventario.objects.create(insumo=ins, tipo=tipo_movimiento, cantidad=qty * det.cantidad, unidad_movimiento=ins.unidad, usuario=usuario, nota=nota_base)
        elif det.mitad_producto:
            ings_prod1 = {ing.insumo.id: ing for ing in det.producto.ingredientes.all()}
            ings_prod2 = {ing.insumo.id: ing for ing in det.mitad_producto.ingredientes.all()}
            for i_id in set(ings_prod1.keys()).union(set(ings_prod2.keys())):
                porcion_removida = removidos_dict.get(i_id, Decimal('0.0'))
                if porcion_removida >= Decimal('1.0'): continue
                
                cantidades = []
                ins = None
                if i_id in ings_prod1:
                    cantidades.append(ings_prod1[i_id].cantidad)
                    ins = ings_prod1[i_id].insumo
                if i_id in ings_prod2:
                    cantidades.append(ings_prod2[i_id].cantidad)
                    if not ins: ins = ings_prod2[i_id].insumo
                
                qty = min(cantidades) * (Decimal(len(cantidades)) / Decimal('2.0'))
                qty = qty * (Decimal('1.0') - porcion_removida)
                if qty > 0 and ins:
                    MovimientoInventario.objects.create(insumo=ins, tipo=tipo_movimiento, cantidad=qty * det.cantidad, unidad_movimiento=ins.unidad, usuario=usuario, nota=nota_base)
        else:
            for ing in det.producto.ingredientes.all():
                porcion_removida = removidos_dict.get(ing.insumo.id, Decimal('0.0'))
                if porcion_removida >= Decimal('1.0'): continue
                
                qty = ing.cantidad * (Decimal('1.0') - porcion_removida)
                if qty > 0:
                    MovimientoInventario.objects.create(insumo=ing.insumo, tipo=tipo_movimiento, cantidad=qty * det.cantidad, unidad_movimiento=ing.insumo.unidad, usuario=usuario, nota=nota_base)
        for extra in det.extras_elegidos.all():
            if extra.precio == Decimal('0.00') or extra.precio == 0:
                cantidad_a_descontar = extra.porcion
            else:
                cantidad_a_descontar = extra.insumo.cantidad_porcion_extra 
                precio_obj = PrecioExtra.objects.filter(insumo=extra.insumo, tamano=det.producto.tamano).first()
                if precio_obj and precio_obj.cantidad > 0: cantidad_a_descontar = precio_obj.cantidad
                cantidad_a_descontar = cantidad_a_descontar * extra.porcion
            
            cantidad_a_descontar = cantidad_a_descontar * det.cantidad
            if cantidad_a_descontar > 0:
                MovimientoInventario.objects.create(insumo=extra.insumo, tipo=tipo_movimiento, cantidad=cantidad_a_descontar, unidad_movimiento=extra.insumo.unidad, usuario=usuario, nota=f"{nota_base} (Extra)")
        
        if det.es_para_llevar:
            config_global = Configuracion.get_solo()
            caja_insumo = None
            if det.producto.tamano == 'IND': caja_insumo = config_global.caja_individual
            elif det.producto.tamano == 'MED': caja_insumo = config_global.caja_mediana
            elif det.producto.tamano == 'FAM': caja_insumo = config_global.caja_familiar
            if caja_insumo:
                MovimientoInventario.objects.create(insumo=caja_insumo, tipo=tipo_movimiento, cantidad=det.cantidad, unidad_movimiento=caja_insumo.unidad, usuario=usuario, nota=f"{nota_base} (Empaque)")

def grabar_mesa_ajax(request, table_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            items = data.get('carrito', [])
            mesero_nombre = data.get('mesero', '')
            is_sync = data.get('is_sync', False)
            imprimir_ticket = data.get('imprimir_ticket', False)
            ignorar_stock = data.get('ignorar_stock', False)

            # --- VALIDACIÓN DE STOCK CORREGIDA Y CENTRALIZADA ---
            if not is_sync and not ignorar_stock: # Solo validamos stock si no es una sincronización previa a facturar
                # Usamos la función central que sí contempla mitades, cuartos, extras, etc.
                insumos_requeridos = calcular_insumos_requeridos_json(items)
                
                faltantes = []
                for insumo_id, cant_requerida in insumos_requeridos.items():
                    try:
                        insumo = Insumo.objects.get(id=insumo_id)
                        if insumo.stock_actual < cant_requerida:
                            faltantes.append(f"Falta {insumo.nombre}: Tienes {insumo.stock_actual:g}, necesitas {cant_requerida:g}")
                    except Insumo.DoesNotExist:
                        # Si un insumo no existe, lo ignoramos en la validación para no romper el flujo
                        continue

                if faltantes:
                    return JsonResponse({'status': 'warning_stock', 'message': "STOCK_INSUFICIENTE|\n" + "\n".join(faltantes)})
            
            table = Table.objects.get(id=table_id)
            
            mesero_obj = None
            if mesero_nombre:
                mesero_obj = User.objects.filter(username=mesero_nombre).first()

            with transaction.atomic():
                orden, created = Orden.objects.get_or_create(mesa=table)
                
                # 1. Reponer inventario si estamos editando una orden existente
                if not created and orden.detalles.exists():
                    procesar_inventario_orden(orden, request.user, f"Rep. edición Mesa {table.number}", 'ENTRADA')

                # Borrar items viejos y aplicar nuevos
                orden.detalles.all().delete()
                orden.mesero = mesero_obj
                orden.save()

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
                        es_para_llevar=item.get('para_llevar', False),
                        impreso=not item.get('es_nuevo', False)
                    )
                    
                    mitad_id = item.get('mitad_id')
                    cuarto_2_id = item.get('cuarto_2_id')
                    cuarto_3_id = item.get('cuarto_3_id')
                    cuarto_4_id = item.get('cuarto_4_id')
                    
                    if cuarto_2_id and cuarto_3_id and cuarto_4_id:
                        nuevo_detalle.cuarto_2_producto = Producto.objects.get(id=cuarto_2_id)
                        nuevo_detalle.cuarto_3_producto = Producto.objects.get(id=cuarto_3_id)
                        nuevo_detalle.cuarto_4_producto = Producto.objects.get(id=cuarto_4_id)
                        nuevo_detalle.save()
                    elif mitad_id:
                        mitad_obj = Producto.objects.get(id=mitad_id)
                        nuevo_detalle.mitad_producto = mitad_obj
                        nuevo_detalle.save()
                        
                    removidos = item.get('removidos', [])
                    if removidos:
                        for rem_data in removidos:
                            try:
                                if isinstance(rem_data, dict):
                                    rem_id = int(rem_data.get('id', 0))
                                    porcion = Decimal(str(rem_data.get('porcion', 1.0)))
                                else:
                                    rem_id = int(rem_data)
                                    porcion = Decimal('1.0')
                                    
                                if rem_id > 0:
                                    if porcion == Decimal('1.0'):
                                        nuevo_detalle.ingredientes_removidos.add(rem_id)
                                    else:
                                        ins_rem = Insumo.objects.get(id=rem_id)
                                        DetalleOrdenRemovido.objects.create(
                                            detalle_orden=nuevo_detalle,
                                            insumo=ins_rem,
                                            porcion=porcion
                                        )
                            except Exception as e_rem:
                                print(f"Error procesando removido: {e_rem}")

                    # B) GUARDAR EXTRAS
                    ids_extras = item.get('extras', [])
                    if ids_extras:
                        for extra_data in ids_extras:
                            try:
                                if isinstance(extra_data, dict):
                                    extra_id = extra_data.get('id')
                                    porcion = Decimal(str(extra_data.get('porcion', 1.0)))
                                    es_sustituto = extra_data.get('es_sustituto', False)
                                else:
                                    extra_id = extra_data
                                    porcion = Decimal('1.0')
                                    es_sustituto = False
                                    
                                insumo = Insumo.objects.get(id=extra_id)
                                
                                # LÓGICA CORREGIDA: Buscar precio según tamaño del producto
                                precio_final = insumo.precio_venta_extra # Valor por defecto
                                
                                # Buscamos si existe un precio configurado para este tamaño
                                precio_obj = PrecioExtra.objects.filter(
                                    insumo=insumo, 
                                    tamano=prod_obj.tamano
                                ).first()
                                
                                if precio_obj:
                                    precio_final = precio_obj.precio
                                    
                                precio_cobrado = Decimal('0.00') if es_sustituto else (precio_final * porcion)

                                DetalleOrdenExtra.objects.create(
                                    detalle_orden=nuevo_detalle,
                                    insumo=insumo,
                                    precio=precio_cobrado,
                                    porcion=porcion
                                )
                            except Insumo.DoesNotExist:
                                print(f"Error: Insumo ID {extra_id} no existe.")
                            except Exception as e_extra:
                                print(f"Error guardando extra: {e_extra}")
                                
                # 4. Descontar el inventario de la nueva orden recién grabada
                procesar_inventario_orden(orden, request.user, f"Orden Mesa {table.number}", 'SALIDA')

            # 4. Actualizar Mesa
            table.is_occupied = True
            table.mesero = mesero_obj
            table.save()
            
            if not is_sync and imprimir_ticket: # Si NO es sincronización Y se solicitó imprimir
                from .utils_impresora import imprimir_comanda
                imprimir_comanda(orden)
            return JsonResponse({'status': 'ok', 'orden_id': orden.id, 'imprimir': imprimir_ticket})
            
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
    return HttpResponse(html)

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
                # Restablecer el inventario de la orden eliminada
                procesar_inventario_orden(orden, request.user, f"Eliminación Mesa {table.number} - {motivo}", 'ENTRADA')
                orden.delete()
            
            table.is_occupied = False
            table.solicitud_pago = False
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
            'extras_elegidos': item.extras_elegidos.all(),
            'mitad_producto': item.mitad_producto.nombre if item.mitad_producto else None,
            'cuarto_2_producto': item.cuarto_2_producto.nombre if item.cuarto_2_producto else None,
            'cuarto_3_producto': item.cuarto_3_producto.nombre if item.cuarto_3_producto else None,
            'cuarto_4_producto': item.cuarto_4_producto.nombre if item.cuarto_4_producto else None,
            'ingredientes_removidos': item.ingredientes_removidos,
            'removidos_detalles': getattr(item, 'removidos_detalles', None)
        })

    # Calculamos el total en Bs basado en el nuevo total USD
    total_acumulado_bs = total_acumulado_usd * tasa_valor
    imprimir_precuenta(orden, tasa_valor)

    # --- Si la petición viene en segundo plano, terminamos aquí ---
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok', 'mensaje': 'Enviado a impresora'})

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
    return HttpResponse(html)

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

            if not orden.impreso:
                from .utils_impresora import imprimir_comanda
                imprimir_comanda(orden)

            # --- 1. RECALCULAR TOTALES REALES (Base + Extras) ---
            total_venta_real = 0
            for det in orden.detalles.all():
                precio_base = float(det.precio_unitario)
                costo_extras = sum(float(e.precio) for e in det.extras_elegidos.all())
                subtotal_linea = (precio_base + costo_extras) * det.cantidad
                total_venta_real += subtotal_linea
            
            diferencia = monto_total_recibido - total_venta_real
            propina_calc = diferencia if (diferencia > 0 and es_propina) else 0

            # --- 3. TRANSACCIÓN DE GUARDADO ---
            with transaction.atomic():
                # Numeración
                ultima = Venta.objects.last()
                nuevo_num = (int(ultima.codigo_factura) + 1) if (ultima and ultima.codigo_factura.isdigit()) else 1
                codigo = f"{nuevo_num:06d}"

                metodo_general = 'MIXTO' if len(lista_pagos) > 1 else lista_pagos[0]['metodo']
                
                config_solo = Configuracion.get_solo()
                tasa_usar = config_solo.tasa_dolar
                
                tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
                tasa_bcv_real = tasa_obj.precio if tasa_obj else config_solo.tasa_dolar
                
                if config_solo.usar_scraping_bcv:
                    tasa_usar = tasa_bcv_real
                    
                tiene_cashea = any(p.get('metodo') == 'CASHEA' for p in lista_pagos)
                if tiene_cashea:
                    if config_solo.usar_tasa_bcv_para_cashea:
                        tasa_usar = tasa_bcv_real
                    else:
                        if config_solo.tasa_cashea > 0:
                            tasa_usar = config_solo.tasa_cashea

                # Crear Venta con el TOTAL REAL RECALCULADO
                venta = Venta.objects.create(
                    codigo_factura=codigo,
                    total=total_venta_real,
                    metodo_pago=metodo_general,
                    mesero=orden.mesero,
                    mesa_numero=table.number,
                    monto_recibido=monto_total_recibido,
                    propina=propina_calc,
                    tasa_aplicada=tasa_usar
                )

                # Registrar Pagos
                for p in lista_pagos:
                    Pago.objects.create(venta=venta, metodo=p['metodo'], monto=p['monto'])

                # Procesar Detalles
                for det in orden.detalles.all():
                    precio_base = float(det.precio_unitario)
                    costo_extras = sum(float(e.precio) for e in det.extras_elegidos.all())
                    subtotal_real = (precio_base + costo_extras) * det.cantidad
                    
                    nombre_con_tamano = det.producto.nombre
                    if det.producto.tamano != 'UNI':
                        nombre_con_tamano += f" ({det.producto.get_tamano_display() if hasattr(det.producto, 'get_tamano_display') else det.producto.tamano})"

                    dv = DetalleVenta.objects.create(
                        venta=venta, 
                        producto=det.producto, 
                        nombre_producto=nombre_con_tamano,
                        cantidad=det.cantidad, 
                        precio_unitario=det.precio_unitario, 
                        subtotal=subtotal_real,
                        mitad_producto=det.mitad_producto,
                        nombre_mitad=det.mitad_producto.nombre if det.mitad_producto else None,
                        cuarto_2_producto=det.cuarto_2_producto,
                        nombre_cuarto_2=det.cuarto_2_producto.nombre if det.cuarto_2_producto else None,
                        cuarto_3_producto=det.cuarto_3_producto,
                        nombre_cuarto_3=det.cuarto_3_producto.nombre if det.cuarto_3_producto else None,
                        cuarto_4_producto=det.cuarto_4_producto,
                        nombre_cuarto_4=det.cuarto_4_producto.nombre if det.cuarto_4_producto else None
                    )
                    
                    if det.ingredientes_removidos.exists():
                        for ing_rem in det.ingredientes_removidos.all():
                            dv.ingredientes_removidos.add(ing_rem)
                            
                    # Guardamos los extras en el histórico
                    for extra_orden in det.extras_elegidos.all():
                        DetalleVentaExtra.objects.create(
                            detalle_venta=dv,
                            nombre_extra=extra_orden.insumo.nombre,
                            precio=extra_orden.precio,
                            porcion=extra_orden.porcion
                        )

                orden.delete()
                table.is_occupied = False
                table.solicitud_pago = False
                table.solicitud_pago = False
                table.mesero = None
                table.save()

            # =========================================================
            # IMPRESIÓN FÍSICA DIRECTA A LA TICKERA
            # =========================================================
            impreso_ok, mensaje_print = mandar_a_tickera(venta)

            return JsonResponse({
                'status': 'ok', 
                'venta_id': venta.id,
                'impreso_fisico': impreso_ok,
                'mensaje_impresion': mensaje_print
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error'}, status=400)
@staff_member_required

def generar_factura_pdf(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_valor = float(tasa_obj.precio) if tasa_obj else 0
    tasa_uso = float(venta.tasa_aplicada) if venta.tasa_aplicada else tasa_valor
    total_bs = float(venta.total) * tasa_uso
    config_negocio = Configuracion.get_solo()

    context = {
        'venta': venta,
        'detalles': venta.detalles.all(),
        'tasa': tasa_uso,
        'total_bs': total_bs,
        'vuelto': float(venta.monto_recibido) - float(venta.total) - float(venta.propina),
        'config': config_negocio
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
    return HttpResponse(html)

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
                    
                    removidos_dict = {}
                    for r in detalle.ingredientes_removidos.all():
                        removidos_dict[r.id] = Decimal('1.0')
                    if hasattr(detalle, 'removidos_detalles'):
                        for r in detalle.removidos_detalles.all():
                            if r.insumo: removidos_dict[r.insumo.id] = r.porcion
                            
                    if getattr(detalle, 'cuarto_2_producto', None) and getattr(detalle, 'cuarto_3_producto', None) and getattr(detalle, 'cuarto_4_producto', None):
                        ings_prod1 = {ing.insumo.id: ing for ing in producto.ingredientes.all()} if producto else {}
                        ings_prod2 = {ing.insumo.id: ing for ing in detalle.cuarto_2_producto.ingredientes.all()} if detalle.cuarto_2_producto else {}
                        ings_prod3 = {ing.insumo.id: ing for ing in detalle.cuarto_3_producto.ingredientes.all()} if detalle.cuarto_3_producto else {}
                        ings_prod4 = {ing.insumo.id: ing for ing in detalle.cuarto_4_producto.ingredientes.all()} if detalle.cuarto_4_producto else {}
                        
                        all_i_ids = set(ings_prod1.keys()) | set(ings_prod2.keys()) | set(ings_prod3.keys()) | set(ings_prod4.keys())
                        for i_id in all_i_ids:
                            porcion_removida = removidos_dict.get(i_id, Decimal('0.0'))
                            if porcion_removida >= Decimal('1.0'): continue
                            
                            cantidades = []
                            ins = None
                            if i_id in ings_prod1: 
                                cantidades.append(ings_prod1[i_id].cantidad)
                                ins = ings_prod1[i_id].insumo
                            if i_id in ings_prod2: 
                                cantidades.append(ings_prod2[i_id].cantidad)
                                if not ins: ins = ings_prod2[i_id].insumo
                            if i_id in ings_prod3: 
                                cantidades.append(ings_prod3[i_id].cantidad)
                                if not ins: ins = ings_prod3[i_id].insumo
                            if i_id in ings_prod4: 
                                cantidades.append(ings_prod4[i_id].cantidad)
                                if not ins: ins = ings_prod4[i_id].insumo
                            
                            qty = min(cantidades) * (Decimal(len(cantidades)) / Decimal('4.0'))
                            qty = qty * (Decimal('1.0') - porcion_removida)
                            if qty > 0 and ins:
                                nota_mov = f"ANULACIÓN Venta #{venta.codigo_factura}: 4 Cuartos {producto.nombre[:10]}..."
                                MovimientoInventario.objects.create(insumo=ins, tipo='ENTRADA', cantidad=qty * cantidad_vendida, unidad_movimiento=ins.unidad, usuario=request.user, nota=nota_mov, costo_unitario_movimiento=ins.costo_unitario)
                    elif detalle.mitad_producto:
                        if producto:
                            ings_prod1 = {ing.insumo.id: ing for ing in producto.ingredientes.all()}
                            ings_prod2 = {ing.insumo.id: ing for ing in detalle.mitad_producto.ingredientes.all()}
                            
                            for i_id in set(ings_prod1.keys()).union(set(ings_prod2.keys())):
                                porcion_removida = removidos_dict.get(i_id, Decimal('0.0'))
                                if porcion_removida >= Decimal('1.0'): continue
                                
                                cantidades = []
                                insumo_usado = None
                                if i_id in ings_prod1:
                                    cantidades.append(ings_prod1[i_id].cantidad)
                                    insumo_usado = ings_prod1[i_id].insumo
                                if i_id in ings_prod2:
                                    cantidades.append(ings_prod2[i_id].cantidad)
                                    if not insumo_usado: insumo_usado = ings_prod2[i_id].insumo
                                    
                                qty = min(cantidades) * (Decimal(len(cantidades)) / Decimal('2.0'))
                                nota_mov = f"ANULACIÓN Venta #{venta.codigo_factura}: Mitad/Mitad"

                                qty = qty * (Decimal('1.0') - porcion_removida)
                                if qty > 0:
                                    MovimientoInventario.objects.create(
                                        insumo=insumo_usado, tipo='ENTRADA',
                                        cantidad=qty * cantidad_vendida,
                                        unidad_movimiento=insumo_usado.unidad,
                                        usuario=request.user,
                                        nota=nota_mov,
                                        costo_unitario_movimiento=insumo_usado.costo_unitario 
                                    )
                    else:
                        if producto:
                            for ingrediente in producto.ingredientes.all():
                                porcion_removida = removidos_dict.get(ingrediente.insumo.id, Decimal('0.0'))
                                if porcion_removida >= Decimal('1.0'): continue
                                
                                qty = ingrediente.cantidad * (Decimal('1.0') - porcion_removida)
                                if qty > 0:
                                    MovimientoInventario.objects.create(
                                        insumo=ingrediente.insumo, tipo='ENTRADA',
                                        cantidad=qty * cantidad_vendida,
                                        unidad_movimiento=ingrediente.insumo.unidad,
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
    insumos_list = Insumo.objects.filter(es_extra=True).order_by('nombre')
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
    for insumo in insumos_list:
        insumo.id_str = str(insumo.id)
        
    paginator = Paginator(insumos_list, 10)
    page_number = request.GET.get('page')
    insumos = paginator.get_page(page_number)

    return render(request, 'products/manage_extras.html', {
        'insumos': insumos,
        'tamanos': tamanos,
        'datos': diccionario_datos
    })