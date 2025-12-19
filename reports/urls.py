from django.urls import path
from . import views

urlpatterns = [
    path('', views.reportes_index, name='reportes_index'), # Menú principal
    path('inventario/', views.reporte_inventario, name='reporte_inventario'),
    path('meseros/', views.ventas_mesero, name='ventas_mesero'),
    path('productos/', views.ventas_producto, name='ventas_producto'),
    path('pagos/', views.ventas_pago, name='ventas_pago'),
    path('auditoria/', views.auditoria_eliminaciones, name='auditoria_eliminaciones'),
]