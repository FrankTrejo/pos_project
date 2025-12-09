
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_table, name='create_table'),
    # Ruta específica para la petición AJAX de cambiar estado
    path('toggle/<int:table_id>/', views.toggle_status, name='toggle_status'),
    # Esta ruta captura el ID de la mesa en la URL, ej: /table/5/order/
    path('table/<int:table_id>/order/', views.table_order_view, name='table_order'),
]