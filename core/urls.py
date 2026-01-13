from django.urls import path
from . import views

urlpatterns = [
    # Menú Principal de Configuración
    path('configuracion/', views.configuracion_menu, name='configuracion_menu'),

    # Sub-páginas independientes
    path('configuracion/identidad/', views.editar_identidad, name='conf_identidad'),
    path('configuracion/economia/', views.editar_economia, name='conf_economia'),
    path('configuracion/visual/', views.editar_visual, name='conf_visual'),
]