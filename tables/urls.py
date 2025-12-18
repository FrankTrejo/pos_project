
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

    # 1. Catálogo General
    path('productos/', views.product_list, name='product_list'),
    
    # 2. PASO 1: Crear/Editar Datos Básicos
    path('productos/nuevo/', views.product_create, name='product_create'),
    path('productos/editar-datos/<int:pk>/', views.product_create, name='product_edit_basic'), # <--- OJO CON ESTE NOMBRE
    
    # 3. PASO 2: Receta (Ingredientes)
    path('productos/receta/<int:pk>/', views.recipe_manager, name='recipe_manager'),
    
    # 4. PASO 3: Precio (Nuevo)
    path('productos/precio/<int:pk>/', views.product_pricing, name='product_pricing'),
    path('productos/eliminar/<int:pk>/', views.product_delete, name='product_delete'),
]
