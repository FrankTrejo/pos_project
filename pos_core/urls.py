
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tables.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('inventory/', include('inventory.urls')),
    path('reportes/', include('reports.urls')),
    path('maestros/', include('maestros.urls')),
    path('core/', include('core.urls')),
]
