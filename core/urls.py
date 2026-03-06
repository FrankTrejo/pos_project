from django.urls import path
from . import views

urlpatterns = [
    # Menú Principal de Configuración
    path('configuracion/', views.configuracion_menu, name='configuracion_menu'),

    # Sub-secciones (Estos son los nombres que faltaban)
    path('configuracion/identidad/', views.conf_identidad, name='conf_identidad'),
    path('configuracion/economia/', views.conf_economia, name='conf_economia'),
    path('configuracion/visual/', views.conf_visual, name='conf_visual'),
]