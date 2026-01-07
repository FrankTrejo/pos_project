from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_index, name='inventory_index'),
    path('movimiento/nuevo/', views.add_movement, name='add_movement'),
    path('nuevo/', views.insumo_create, name='insumo_create'),
    path('movimiento/', views.inventory_move, name='inventory_move'),
    path('composicion/<int:pk>/', views.insumo_composition, name='insumo_composition'),
    path('editar/<int:pk>/', views.insumo_edit, name='insumo_edit'),
    path('eliminar/<int:pk>/', views.insumo_delete, name='insumo_delete'),
    path('produccion/<int:pk>/', views.insumo_produccion, name='insumo_produccion'),
    path('salidas-especiales/', views.salidas_especiales_view, name='salidas_especiales'),
    path('comanda-interna/<int:consumo_id>/pdf/', views.generar_comanda_interno_pdf, name='generar_comanda_interno_pdf'),
]