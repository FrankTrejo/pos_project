from django.urls import path
from . import views

urlpatterns = [
    # 1. Dashboard Principal
    path('', views.inventory_index, name='inventory_index'),

    # 2. Creación de Recetas (El flujo nuevo)
    path('receta/nueva/', views.receta_create, name='receta_create'),
    
    # IMPORTANTE: Cambié <int:pk> por <int:insumo_id> para que coincida con tu vista
    path('composicion/<int:insumo_id>/', views.insumo_composition, name='insumo_composition'),

    # 3. Creación de Productos de Compra (Maestro antiguo)
    # Nota: Asegúrate de que este 'insumo_create' sea el del Maestro o el de Inventario según tu lógica.
    # Si usas el maestro_create desde la app 'maestros', esta línea quizás sobre o deba apuntar allá.
    path('nuevo/', views.insumo_create, name='insumo_create'),

    # 4. Movimientos y Operaciones
    path('movimiento/nuevo/', views.add_movement, name='add_movement'),
    path('movimiento/', views.inventory_move, name='inventory_move'), # Esta parece redundante con la de arriba, revisa cuál usas
    
    # 5. Edición y Eliminación
    path('editar/<int:pk>/', views.insumo_edit, name='insumo_edit'),
    path('eliminar/<int:pk>/', views.insumo_delete, name='insumo_delete'),
    
    # 6. Producción (Cocinar)
    path('produccion/<int:pk>/', views.insumo_produccion, name='insumo_produccion'),
    
    # 7. Extras
    path('salidas-especiales/', views.salidas_especiales_view, name='salidas_especiales'),
    path('comanda-interna/<int:consumo_id>/pdf/', views.generar_comanda_interno_pdf, name='generar_comanda_interno_pdf'),
]