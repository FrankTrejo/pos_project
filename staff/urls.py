# staff/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.staff_list, name='staff_list'),
    path('crear/', views.staff_create, name='staff_create'),
    path('editar/<int:pk>/', views.staff_edit, name='staff_edit'),
    path('eliminar/<int:pk>/', views.staff_delete, name='staff_delete'),
]