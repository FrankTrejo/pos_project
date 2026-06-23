from django.urls import path
from . import views

urlpatterns = [
    path('', views.reportes_index, name='reportes_index'), # Menú principal
    path('inventario/', views.reporte_inventario, name='reporte_inventario'),
    path('meseros/', views.ventas_mesero, name='ventas_mesero'),
    path('productos/', views.ventas_producto, name='ventas_producto'),
    path('pagos/', views.ventas_pago, name='ventas_pago'),
    path('auditoria/', views.auditoria_eliminaciones, name='auditoria_eliminaciones'),
    path('ventas-detalle/', views.reporte_ventas_detalle, name='reporte_ventas_detalle'),
    path('insumos-agotados/', views.reporte_insumos_agotados, name='reporte_insumos_agotados'),
    path('historial-tasas/', views.historial_tasas_bcv, name='historial_tasas_bcv'),
    path('propinas/', views.reporte_propinas, name='reporte_propinas'),
    path('venta/<int:venta_id>/detalle/', views.detalle_venta_view, name='detalle_venta'),
    path('cuadre/', views.cuadre_caja_list, name='cuadre_caja_list'),
    path('cuadre/nuevo/', views.cuadre_caja_nuevo, name='cuadre_caja_nuevo'),

]