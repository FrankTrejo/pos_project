from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_index, name='inventory_index'),
    path('movimiento/nuevo/', views.add_movement, name='add_movement'),
    path('nuevo/', views.insumo_create, name='insumo_create'),
    path('movimiento/', views.inventory_move, name='inventory_move'),
    path('composicion/<int:pk>/', views.insumo_composition, name='insumo_composition'),
]