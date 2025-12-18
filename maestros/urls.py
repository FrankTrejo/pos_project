from django.urls import path
from . import views

urlpatterns = [
    path('', views.maestro_list, name='maestro_list'),
    path('nuevo/', views.maestro_create, name='maestro_create'),
    path('editar/<int:pk>/', views.maestro_edit, name='maestro_edit'),
]