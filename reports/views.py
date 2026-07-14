from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import timedelta
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from .models import AuditoriaEliminacion, AuditoriaConfiguracion
from decimal import Decimal
from django.http import HttpResponse

# Importamos modelos de ambas aplicaciones (Inventario y Ventas)
from inventory.models import Insumo, MovimientoInventario
from tables.models import Venta, DetalleVenta, TasaBCV

# 1. MENÚ PRINCIPAL DE REPORTES (Centro de Mando)
@never_cache
@staff_member_required
def reportes_index(request):
    """Muestra el panel con las tarjetas de opciones"""
    return render(request, 'reports/index.html')

# 2. REPORTE DE INVENTARIO (Completo)
@never_cache
@staff_member_required
def reporte_inventario(request):
    # Filtros de fecha (Por defecto: Últimos 30 días)
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if not fecha_inicio:
        fecha_inicio = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not fecha_fin:
        fecha_fin = timezone.now().strftime('%Y-%m-%d')

    # KPIs Generales
    insumos = Insumo.objects.all()
    
    # Cálculo seguro del valor total
    valor_total_inventario = sum(i.stock_actual * i.costo_unitario for i in insumos)
    
    items_bajo_stock = insumos.filter(stock_actual__lte=F('stock_minimo')).count()
    
    # Datos para gráficos (Top 5 Consumo)
    movimientos_rango = MovimientoInventario.objects.filter(
        fecha__date__range=[fecha_inicio, fecha_fin]
    )
    
    top_consumo = (movimientos_rango.filter(tipo='SALIDA')
                   .values('insumo__nombre')
                   .annotate(total_cantidad=Sum('cantidad'))
                   .order_by('-total_cantidad')[:5])
    
    labels_chart = [item['insumo__nombre'] for item in top_consumo]
    data_chart = [float(item['total_cantidad']) for item in top_consumo]

    # Tabla detallada
    movimientos_tabla = movimientos_rango.select_related('insumo', 'usuario').order_by('-fecha')

    paginator = Paginator(movimientos_tabla, 10)
    page_number = request.GET.get('page')
    movimientos = paginator.get_page(page_number)

    context = {
        'valor_total': valor_total_inventario,
        'bajo_stock': items_bajo_stock,
        'total_items': insumos.count(),
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'labels_chart': labels_chart,
        'data_chart': data_chart,
        'movimientos': movimientos,
    }
    
    return render(request, 'reports/inventory_report.html', context)

# 3. REPORTE VENTAS X MESERO
@never_cache
@staff_member_required
def ventas_mesero(request):
    fecha_inicio = request.GET.get('fecha_inicio', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fecha_fin', timezone.now().strftime('%Y-%m-%d'))

    # Agrupamos ventas por Mesero
    data = (Venta.objects.filter(fecha__date__range=[fecha_inicio, fecha_fin], anulada=False)
            .values('mesero__username')
            .annotate(total_vendido=Sum('total'), total_ordenes=Count('id'))
            .order_by('-total_vendido'))

    # Preparamos datos para Chart.js
    labels = [item['mesero__username'] if item['mesero__username'] else 'Sin Asignar' for item in data]
    values = [float(item['total_vendido']) for item in data]
    data = Paginator(data, 10).get_page(request.GET.get('page'))

    context = {
        'titulo': 'Ventas por Mesero',
        'data_tabla': data,
        'labels': labels,
        'values': values,
        'tipo_chart': 'bar', # Gráfico de Barras
        'fecha_inicio': fecha_inicio, 
        'fecha_fin': fecha_fin
    }
    return render(request, 'reports/generic_sales_report.html', context)

# 4. REPORTE VENTAS X PRODUCTO
@never_cache
@staff_member_required
def ventas_producto(request):
    fecha_inicio = request.GET.get('fecha_inicio', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fecha_fin', timezone.now().strftime('%Y-%m-%d'))

    # Agrupamos detalles por Producto (Top 10)
    data_qs = (DetalleVenta.objects.filter(venta__fecha__date__range=[fecha_inicio, fecha_fin], venta__anulada=False)
            .values('nombre_producto', 'nombre_mitad')
            .annotate(cantidad_total=Sum('cantidad'), dinero_generado=Sum('subtotal'))
            .order_by('-cantidad_total')[:10])

    labels = []
    data_list = []
    
    for item in data_qs:
        if item.get('nombre_mitad'):
            nombre_completo = f"1/2 {item['nombre_producto']} + 1/2 {item['nombre_mitad']}"
        else:
            nombre_completo = item['nombre_producto']
            
        labels.append(nombre_completo)
        data_list.append({
            'nombre_producto': nombre_completo,
            'cantidad_total': item['cantidad_total'],
            'dinero_generado': item['dinero_generado']
        })

    values = [float(item['cantidad_total']) for item in data_qs] 
    data_paginada = Paginator(data_list, 10).get_page(request.GET.get('page'))

    context = {
        'titulo': 'Top Productos Vendidos (Unidades)',
        'data_tabla': data_paginada,
        'labels': labels,
        'values': values,
        'tipo_chart': 'doughnut', # Gráfico de Dona
        'fecha_inicio': fecha_inicio, 
        'fecha_fin': fecha_fin,
        'is_product_report': True # Bandera para ajustar la tabla HTML
    }
    return render(request, 'reports/generic_sales_report.html', context)

@never_cache
@staff_member_required
def auditoria_eliminaciones(request):
    logs_list = AuditoriaEliminacion.objects.all().order_by('-fecha')
    logs_config_list = AuditoriaConfiguracion.objects.all().order_by('-fecha')
    
    paginator_logs = Paginator(logs_list, 10)
    logs = paginator_logs.get_page(request.GET.get('page_logs'))
    
    paginator_config = Paginator(logs_config_list, 10)
    logs_config = paginator_config.get_page(request.GET.get('page_config'))

    return render(request, 'reports/auditoria_list.html', {
        'logs': logs,
        'logs_config': logs_config
    })

# 7. HISTORIAL DE TASAS DE CAMBIO
@never_cache
@staff_member_required
def historial_tasas_bcv(request):
    tasas_list = TasaBCV.objects.all().order_by('-fecha_actualizacion')
    
    # Interceptamos la lista y la paginamos de a 20 registros
    paginator = Paginator(tasas_list, 10) 
    page_number = request.GET.get('page')
    tasas = paginator.get_page(page_number)
    
    return render(request, 'reports/tasa_bcv_history.html', {'tasas': tasas})

# reports/views.py

@never_cache
@staff_member_required
def reporte_ventas_detalle(request):
    # 1. Filtros de Fecha
    # Por defecto, siempre mostrar HOY al ingresar al reporte
    hoy_str = timezone.localtime().date().strftime('%Y-%m-%d')
    fecha_inicio = request.GET.get('fecha_inicio', hoy_str)
    fecha_fin = request.GET.get('fecha_fin', hoy_str)
    
    # 2. Capturamos el filtro de estado (todas, validas, anuladas)
    estado_filtro = request.GET.get('estado', 'todas') # Por defecto 'todas'

    # 3. Consulta Base (Por fecha)
    ventas_list = Venta.objects.filter(
        fecha__date__range=[fecha_inicio, fecha_fin]
    ).select_related('mesero').prefetch_related('detalles', 'pagos').order_by('-fecha')

    # 4. APLICACIÓN DE FILTROS Y CÁLCULO DE TOTALES
    total_periodo = 0
    total_propina = 0

    if estado_filtro == 'anuladas':
        # CASO A: Solo ver las canceladas
        ventas_list = ventas_list.filter(anulada=True)
        # El total muestra cuánto dinero se "perdió" en anulaciones
        total_periodo = ventas_list.aggregate(Sum('total'))['total__sum'] or 0
        total_propina = ventas_list.aggregate(Sum('propina'))['propina__sum'] or 0

    elif estado_filtro == 'validas':
        # CASO B: Solo ver las cobradas
        ventas_list = ventas_list.filter(anulada=False)
        total_periodo = ventas_list.aggregate(Sum('total'))['total__sum'] or 0
        total_propina = ventas_list.aggregate(Sum('propina'))['propina__sum'] or 0

    else:
        # CASO C: Ver todas (Mix)
        # Aquí mostramos la lista completa, pero el total SUMA SOLO LO REAL (No anulado)
        total_periodo = ventas_list.filter(anulada=False).aggregate(Sum('total'))['total__sum'] or 0
        total_propina = ventas_list.filter(anulada=False).aggregate(Sum('propina'))['propina__sum'] or 0

    # Calcular equivalente en bolívares usando la tasa actual
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_valor = float(tasa_obj.precio) if tasa_obj else 0
    total_periodo_bs = float(total_periodo) * tasa_valor

    # Detectamos si el usuario presionó el botón de exportar
    if request.GET.get('exportar') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="ventas_detalle_{fecha_inicio}_al_{fecha_fin}.csv"'
        
        # Formato UTF-8 BOM para que Excel detecte acentos
        response.write(u'\ufeff'.encode('utf8'))
        writer = csv.writer(response, delimiter=';')
        
        writer.writerow(['Fecha', 'Hora', 'N Factura', 'Mesero', 'Productos', 'Metodo Pago', 'Estado', 'Propina ($)', 'Total ($)'])
        
        for v in ventas_list:
            mesero_nombre = v.mesero.username.title() if v.mesero else "Sin Asignar"
            
            prods = []
            for d in v.detalles.all():
                prods.append(f"{d.cantidad}x {d.nombre_producto}")
            productos_str = " | ".join(prods)
            
            if v.pagos.exists():
                pagos_list = [f"{p.get_metodo_display()} (${p.monto})" for p in v.pagos.all()]
                pagos_str = " + ".join(pagos_list)
            else:
                pagos_str = v.get_metodo_pago_display()
                
            estado_str = "ANULADA" if v.anulada else "COBRADA"
            
            writer.writerow([
                v.fecha.strftime("%d/%m/%Y"),
                v.fecha.strftime("%H:%M"),
                v.codigo_factura,
                mesero_nombre,
                productos_str,
                pagos_str,
                estado_str,
                f"{float(v.propina):.4f}".replace('.', ','),
                f"{float(v.total):.2f}".replace('.', ',')
            ])
            
        return response

    paginator = Paginator(ventas_list, 10)
    page_number = request.GET.get('page')
    ventas = paginator.get_page(page_number)

    # Agregamos el cálculo en Bs a cada venta de esta página
    for v in ventas:
        v.total_bs = float(v.total) * tasa_valor
        v.propina_bs = float(v.propina) * tasa_valor

    context = {
        'ventas': ventas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_periodo': total_periodo,
        'total_periodo_bs': total_periodo_bs,
        'total_propina': total_propina,
        'estado_filtro': estado_filtro # Pasamos esto para pintar los botones
    }
    return render(request, 'reports/sales_detail_report.html', context)

@never_cache
@staff_member_required
def detalle_venta_view(request, venta_id):
    venta = get_object_or_404(
        Venta.objects.select_related('mesero')
                     .prefetch_related('detalles__producto', 
                                       'detalles__mitad_producto', 
                                       'detalles__ingredientes_removidos',
                                       'detalles__cuarto_2_producto',
                                       'detalles__cuarto_3_producto',
                                       'detalles__cuarto_4_producto',
                                       'detalles__extras',
                                       'pagos'), 
        id=venta_id
    )

    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_valor = float(tasa_obj.precio) if tasa_obj else 0

    # Calcular total de la propina en bolívares
    propina_bs = float(venta.propina) * tasa_valor

    context = {
        'venta': venta,
        'tasa_bcv_actual': tasa_valor,
        'propina_bs': propina_bs
    }

    return render(request, 'reports/venta_detalle.html', context)


# reports/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import F, ExpressionWrapper, DecimalField
from inventory.models import Insumo

@never_cache
@login_required
def reporte_insumos_agotados(request):
    # CORRECCIÓN: Usamos 'stock_actual' en lugar de 'cantidad'
    insumos_criticos_list = Insumo.objects.filter(
        stock_actual__lte=F('stock_minimo')
    ).annotate(
        deficit=ExpressionWrapper(
            F('stock_minimo') - F('stock_actual'),
            output_field=DecimalField()
        )
    ).order_by('stock_actual') 
    
    paginator = Paginator(insumos_criticos_list, 10)
    page_number = request.GET.get('page')
    insumos_criticos = paginator.get_page(page_number)

    return render(request, 'reports/insumos_agotados.html', {
        'insumos': insumos_criticos
    })

@never_cache
@staff_member_required
def reporte_propinas(request):
    hoy_str = timezone.localtime().date().strftime('%Y-%m-%d')
    fecha_inicio = request.GET.get('fecha_inicio', hoy_str)
    fecha_fin = request.GET.get('fecha_fin', hoy_str)

    ventas_list = Venta.objects.filter(
        fecha__date__range=[fecha_inicio, fecha_fin],
        propina__gt=0,
        anulada=False
    ).select_related('mesero').order_by('-fecha')

    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_valor = float(tasa_obj.precio) if tasa_obj else 0

    # Detectamos si el usuario presionó el botón de exportar
    if request.GET.get('exportar') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="propinas_{fecha_inicio}_al_{fecha_fin}.csv"'
        
        # Le agregamos el formato BOM para que Excel lea los caracteres en español sin problemas (UTF-8)
        response.write(u'\ufeff'.encode('utf8'))
        writer = csv.writer(response, delimiter=';')
        
        # Escribimos las cabeceras
        writer.writerow(['Fecha', 'Hora', 'N Factura', 'Mesa', 'Mesero', 'Tasa (Bs/$)', 'Propina ($)', 'Propina (Bs)'])
        
        # Escribimos los datos, cambiando el punto decimal por coma para Excel en español
        for v in ventas_list:
            mesero_nombre = v.mesero.username.title() if v.mesero else "Sin Asignar"
            propina_bs = float(v.propina) * tasa_valor
            writer.writerow([
                v.fecha.strftime("%d/%m/%Y"),
                v.fecha.strftime("%H:%M"),
                v.codigo_factura,
                f"Mesa {v.mesa_numero}",
                mesero_nombre,
                f"{tasa_valor:.2f}".replace('.', ','),
                f"{float(v.propina):.4f}".replace('.', ','),
                f"{propina_bs:.2f}".replace('.', ',')
            ])
            
        return response

    total_propina = ventas_list.aggregate(Sum('propina'))['propina__sum'] or 0
    total_propina_bs = float(total_propina) * tasa_valor

    paginator = Paginator(ventas_list, 10)
    page_number = request.GET.get('page')
    ventas = paginator.get_page(page_number)
    
    for v in ventas:
        v.propina_bs = float(v.propina) * tasa_valor

    context = {
        'ventas': ventas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_propina': total_propina,
        'total_propina_bs': total_propina_bs,
        'tasa': tasa_valor
    }
    return render(request, 'reports/propinas_report.html', context)

@never_cache
@staff_member_required
def ventas_pago(request):
    # 1. POR DEFECTO: Siempre mostrar HOY al ingresar
    hoy_str = timezone.localtime().date().strftime('%Y-%m-%d')
    fecha_inicio_str = request.GET.get('fecha_inicio', hoy_str)
    fecha_fin_str = request.GET.get('fecha_fin', hoy_str)

    # 1. Filtrar estrictamente las VENTAS VÁLIDAS (Excluyendo las anuladas)
    ventas_validas = Venta.objects.filter(
        fecha__date__range=[fecha_inicio_str, fecha_fin_str],
        anulada=False
    ).prefetch_related('pagos')

    # Obtenemos la tasa actual
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_valor = float(tasa_obj.precio) if tasa_obj else 0

    # Diccionario para acumular resultados
    resultados_dict = {}
    
    nombres_metodos = {
        'EFECTIVO_USD': 'Efectivo ($)',
        'EFECTIVO_BS': 'Efectivo (Bs)',
        'PUNTO': 'Punto de Venta',
        'PAGO_MOVIL': 'Pago Móvil',
        'ZELLE': 'Zelle',
        'BINANCE': 'Binance',
        'TRANSFERENCIA': 'Transferencia',
        'MIXTO': 'Mixto (Legacy)'
    }

    # 2. Procesar cada venta individualmente para distribuir exactamente "venta.total"
    for venta in ventas_validas:
        pagos = venta.pagos.all()
        
        if pagos.exists():
            # Ordenamos los pagos: los electrónicos primero, el efectivo de último.
            # Esto asume que si hay vuelto/cambio, se da en efectivo.
            pagos_ordenados = sorted(pagos, key=lambda p: 1 if 'EFECTIVO' in p.metodo else 0)
            
            monto_restante = float(venta.total)
            
            for pago in pagos_ordenados:
                metodo_raw = pago.metodo
                metodo_nombre = nombres_metodos.get(metodo_raw, str(metodo_raw).replace('_', ' ').title())
                
                monto_pago = float(pago.monto)
                # Solo tomamos lo necesario para cubrir la venta, ignorando vueltos o propinas
                monto_a_sumar = min(monto_pago, monto_restante)
                
                if monto_a_sumar > 0:
                    if metodo_nombre not in resultados_dict:
                        resultados_dict[metodo_nombre] = {'transacciones': 0, 'total_dolares': 0}
                    
                    resultados_dict[metodo_nombre]['transacciones'] += 1
                    resultados_dict[metodo_nombre]['total_dolares'] += monto_a_sumar
                    
                    monto_restante -= monto_a_sumar
                    
        else:
            # Ventas antiguas (legacy) que no tienen detalle de pagos
            metodo_raw = venta.metodo_pago
            metodo_nombre = nombres_metodos.get(metodo_raw, str(metodo_raw).replace('_', ' ').title())
            monto_a_sumar = float(venta.total)
            
            if metodo_nombre not in resultados_dict:
                resultados_dict[metodo_nombre] = {'transacciones': 0, 'total_dolares': 0}
                
            resultados_dict[metodo_nombre]['transacciones'] += 1
            resultados_dict[metodo_nombre]['total_dolares'] += monto_a_sumar

    # Formatear para la vista
    resultados = []
    labels = []
    values = []
    
    total_general_dolares = 0
    total_general_bs = 0
    total_transacciones = 0

    for metodo_nombre, data in resultados_dict.items():
        total_usd = data['total_dolares']
        total_bs = total_usd * tasa_valor
        transacciones = data['transacciones']

        resultados.append({
            'metodo_nombre': metodo_nombre,
            'transacciones': transacciones,
            'total_dolares': total_usd,
            'total_bs': total_bs,
        })
        
        labels.append(metodo_nombre)
        values.append(total_usd)
        
        total_general_dolares += total_usd
        total_general_bs += total_bs
        total_transacciones += transacciones

    # Ordenar de mayor a menor ingreso
    resultados = sorted(resultados, key=lambda x: x['total_dolares'], reverse=True)

    context = {
        'titulo': 'Reporte de Métodos de Pago',
        'fecha_inicio': fecha_inicio_str,
        'fecha_fin': fecha_fin_str,
        'resultados': resultados,
        'total_general_dolares': total_general_dolares,
        'total_general_bs': total_general_bs,
        'total_transacciones': total_transacciones,
        'labels': labels,
        'values': values,
    }

    # Apuntamos a la nueva plantilla especializada
    return render(request, 'reports/payment_methods_report.html', context)