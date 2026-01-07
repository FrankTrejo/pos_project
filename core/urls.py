from django.urls import path
from . import views

urlpatterns = [
    path('ajustes/', views.configuracion_view, name='configuracion'),
]