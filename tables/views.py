from django.shortcuts import render

# Create your views here.
# tables/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Max
from .models import Table, Categoria, Producto, TasaBCV
from .scrapping import obtener_tasa_bcv
from django.contrib.auth.models import User
from django.http import JsonResponse
import json

# El punto (.) significa "importa desde la misma carpeta donde estoy"
try:
    from .scrapping import obtener_tasa_bcv
except ImportError:
    # Un seguro por si el archivo no existe o tiene errores, para que Django no explote
    print("ERROR CRÍTICO: No se pudo importar 'scrapping.py'")
    def obtener_tasa_bcv(): return "Error módulo scraping"

def initialize_tables_if_empty():
    """Función auxiliar para crear las 20 mesas iniciales si no existen."""
    if Table.objects.count() == 0:
        tables_to_create = []
        for i in range(1, 21):
            tables_to_create.append(Table(number=i))
        Table.objects.bulk_create(tables_to_create)

def index(request):
    """Vista principal que muestra la cuadrícula."""
    initialize_tables_if_empty()
    tables = Table.objects.all()
    return render(request, 'tables/index.html', {'tables': tables})

def create_table(request):
    """Vista para añadir una nueva mesa al final."""
    # Obtenemos el número de mesa más alto actual
    max_number = Table.objects.aggregate(Max('number'))['number__max']
    new_number = (max_number or 0) + 1
    Table.objects.create(number=new_number)
    return redirect('index')

def toggle_status(request, table_id):
    """Vista AJAX para cambiar el estado de una mesa."""
    if request.method == 'POST':
        table = get_object_or_404(Table, id=table_id)
        table.is_occupied = not table.is_occupied
        table.save()
        # Devolvemos el nuevo estado en formato JSON
        return JsonResponse({'is_occupied': table.is_occupied})
    return JsonResponse({'error': 'Invalid request'}, status=400)

# FUNCIÓN DE LA VISTA DE ORDENES
def table_order_view(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    tasa_actual = obtener_tasa_bcv()
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_numerica = float(tasa_obj.precio) if tasa_obj else 0
    categorias = Categoria.objects.all()
    productos = Producto.objects.select_related('categoria').all()
    
    # --- Obtener lista de meseros ---
    # Filtramos solo usuarios que sean staff o activos. O simplemente todos:
    meseros = User.objects.filter(is_active=True)

    context = {
        'table': table,
        'tasa_cambio': tasa_actual,
        'tasa_numerica': tasa_numerica,
        'categorias': categorias, 
        'productos': productos,
        'meseros': meseros, # Enviamos la lista al HTML
    }
    return render(request, 'tables/order_detail.html', context)

# --- AGREGA ESTA NUEVA VISTA AL FINAL ---
def asignar_mesero(request, table_id):
    """Recibe un ID de usuario por AJAX y lo asigna a la mesa"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            
            table = Table.objects.get(id=table_id)
            
            if user_id:
                user = User.objects.get(id=user_id)
                table.mesero = user
                nombre_mesero = user.username
            else:
                table.mesero = None # Desasignar
                nombre_mesero = ""
                
            table.save()
            return JsonResponse({'status': 'ok', 'mesero': nombre_mesero})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=400)

