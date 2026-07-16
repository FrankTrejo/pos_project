
from django.contrib import admin
from django.urls import path, include
from reports import views as report_views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tables.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('inventory/', include('inventory.urls')),
    path('reportes/', include('reports.urls')),
    path('venta/<int:venta_id>/', report_views.detalle_venta_view, name='detalle_venta'),
    path('maestros/', include('maestros.urls')),
    path('core/', include('core.urls')),
    path('caja/', include('caja.urls')),

    
    # --- 2. RUTAS DE LOGIN Y LOGOUT ---
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('personal/', include('staff.urls')),
]
