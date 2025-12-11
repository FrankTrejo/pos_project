from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_index, name='inventory_index'),
    path('movimiento/nuevo/', views.add_movement, name='add_movement'),
]