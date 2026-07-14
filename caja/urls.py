from django.urls import path
from . import views

urlpatterns = [
    path('', views.cuadre_caja_list, name='cuadre_caja_list'),
    path('nuevo/', views.cuadre_caja_nuevo, name='cuadre_caja_nuevo'),
]