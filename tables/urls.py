
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_table, name='create_table'),
    # Ruta específica para la petición AJAX de cambiar estado
    path('toggle/<int:table_id>/', views.toggle_status, name='toggle_status'),
    # Esta ruta captura el ID de la mesa en la URL, ej: /table/5/order/
    path('table/<int:table_id>/order/', views.table_order_view, name='table_order'),
    path('table/<int:table_id>/asignar_mesero/', views.asignar_mesero, name='asignar_mesero'),

    path('productos/', views.product_list, name='product_list'),
    # PASO 1
    path('productos/nuevo/', views.product_create, name='product_create'),
    path('productos/editar-datos/<int:pk>/', views.product_create, name='product_edit_basic'),
    
    # PASO 2
    path('productos/receta/<int:pk>/', views.recipe_manager, name='recipe_manager'),
    
    # PASO 3 (NUEVO)
    path('productos/precio/<int:pk>/', views.product_pricing, name='product_pricing'),
]