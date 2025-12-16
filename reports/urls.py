from django.urls import path
from . import views

urlpatterns = [
    path('inventario/', views.reporte_inventario, name='reporte_inventario'),
]