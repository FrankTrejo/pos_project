from django.shortcuts import render
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta, datetime
from inventory.models import Insumo, MovimientoInventario, CategoriaInsumo
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def reporte_inventario(request):
    # 1. FILTROS DE FECHA (Por defecto: Últimos 30 días)
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if not fecha_inicio:
        fecha_inicio = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not fecha_fin:
        fecha_fin = timezone.now().strftime('%Y-%m-%d')

    # Convertimos strings a objetos datetime conscientes de la zona horaria si es necesario
    # Para simplificar en SQLite, usaremos filtrado string/date básico de Django

    # 2. KPIs GENERALES (Instantánea actual)
    insumos = Insumo.objects.all()
    
    # Valor Total del Inventario (Stock * Costo Promedio)
    valor_total_inventario = sum(i.stock_actual * i.costo_unitario for i in insumos)
    
    # Conteo de Alertas
    items_bajo_stock = insumos.filter(stock_actual__lte=F('stock_minimo')).count()
    
    # 3. DATOS PARA GRÁFICOS
    # Top 5 Insumos con más SALIDAS (Gasto) en el rango de fechas
    movimientos_rango = MovimientoInventario.objects.filter(
        fecha__date__range=[fecha_inicio, fecha_fin]
    )
    
    # Agrupamos por insumo y sumamos la cantidad de salidas
    top_consumo = (movimientos_rango.filter(tipo='SALIDA')
                   .values('insumo__nombre')
                   .annotate(total_cantidad=Sum('cantidad'))
                   .order_by('-total_cantidad')[:5])
    
    # Preparamos listas para Chart.js
    labels_chart = [item['insumo__nombre'] for item in top_consumo]
    data_chart = [float(item['total_cantidad']) for item in top_consumo]

    # 4. TABLA DE MOVIMIENTOS DETALLADA
    movimientos_tabla = movimientos_rango.select_related('insumo', 'usuario').order_by('-fecha')

    context = {
        'valor_total': valor_total_inventario,
        'bajo_stock': items_bajo_stock,
        'total_items': insumos.count(),
        
        # Filtros
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        
        # Gráficos
        'labels_chart': labels_chart,
        'data_chart': data_chart,
        
        # Tabla
        'movimientos': movimientos_tabla,
    }
    
    return render(request, 'reports/inventory_report.html', context)