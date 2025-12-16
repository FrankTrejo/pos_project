from django.shortcuts import render
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta
from django.contrib.admin.views.decorators import staff_member_required

# Importamos modelos de ambas aplicaciones (Inventario y Ventas)
from inventory.models import Insumo, MovimientoInventario
from tables.models import Venta, DetalleVenta 

# 1. MENÚ PRINCIPAL DE REPORTES (Centro de Mando)
@staff_member_required
def reportes_index(request):
    """Muestra el panel con las tarjetas de opciones"""
    return render(request, 'reports/index.html')

# 2. REPORTE DE INVENTARIO (Completo)
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

    context = {
        'valor_total': valor_total_inventario,
        'bajo_stock': items_bajo_stock,
        'total_items': insumos.count(),
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'labels_chart': labels_chart,
        'data_chart': data_chart,
        'movimientos': movimientos_tabla,
    }
    
    return render(request, 'reports/inventory_report.html', context)

# 3. REPORTE VENTAS X MESERO
@staff_member_required
def ventas_mesero(request):
    fecha_inicio = request.GET.get('fecha_inicio', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fecha_fin', timezone.now().strftime('%Y-%m-%d'))

    # Agrupamos ventas por Mesero
    data = (Venta.objects.filter(fecha__date__range=[fecha_inicio, fecha_fin])
            .values('mesero__username')
            .annotate(total_vendido=Sum('total'), total_ordenes=Count('id'))
            .order_by('-total_vendido'))

    # Preparamos datos para Chart.js
    labels = [item['mesero__username'] if item['mesero__username'] else 'Sin Asignar' for item in data]
    values = [float(item['total_vendido']) for item in data]

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
@staff_member_required
def ventas_producto(request):
    fecha_inicio = request.GET.get('fecha_inicio', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fecha_fin', timezone.now().strftime('%Y-%m-%d'))

    # Agrupamos detalles por Producto (Top 10)
    data = (DetalleVenta.objects.filter(venta__fecha__date__range=[fecha_inicio, fecha_fin])
            .values('nombre_producto')
            .annotate(cantidad_total=Sum('cantidad'), dinero_generado=Sum('subtotal'))
            .order_by('-cantidad_total')[:10])

    labels = [item['nombre_producto'] for item in data]
    values = [float(item['cantidad_total']) for item in data] 

    context = {
        'titulo': 'Top Productos Vendidos (Unidades)',
        'data_tabla': data,
        'labels': labels,
        'values': values,
        'tipo_chart': 'doughnut', # Gráfico de Dona
        'fecha_inicio': fecha_inicio, 
        'fecha_fin': fecha_fin,
        'is_product_report': True # Bandera para ajustar la tabla HTML
    }
    return render(request, 'reports/generic_sales_report.html', context)

# 5. REPORTE VENTAS X MÉTODO DE PAGO
@staff_member_required
def ventas_pago(request):
    fecha_inicio = request.GET.get('fecha_inicio', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fecha_fin', timezone.now().strftime('%Y-%m-%d'))

    # Agrupamos por método de pago
    data = (Venta.objects.filter(fecha__date__range=[fecha_inicio, fecha_fin])
            .values('metodo_pago')
            .annotate(total_vendido=Sum('total'), transacciones=Count('id'))
            .order_by('-total_vendido'))

    labels = [item['metodo_pago'] for item in data]
    values = [float(item['total_vendido']) for item in data]

    context = {
        'titulo': 'Ventas por Método de Pago',
        'data_tabla': data,
        'labels': labels,
        'values': values,
        'tipo_chart': 'pie', # Gráfico de Torta
        'fecha_inicio': fecha_inicio, 
        'fecha_fin': fecha_fin
    }
    return render(request, 'reports/generic_sales_report.html', context)