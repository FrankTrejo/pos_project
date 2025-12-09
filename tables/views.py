from django.shortcuts import render

# Create your views here.
# tables/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Max
from .models import Table

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
    """Vista para la pantalla de pedidos de una mesa específica."""
    table = get_object_or_404(Table, id=table_id)

    # --- AQUÍ LLAMAMOS A TU FUNCIÓN ---
    # Esto ejecutará el script de scraping en tiempo real.
    print("Consultando BCV...") # Opcional: para ver en la consola cuándo ocurre
    tasa_actual = obtener_tasa_bcv()

    context = {
        'table': table,
        # Pasamos el resultado del scraping a la plantilla
        'tasa_cambio': tasa_actual,
    }
    return render(request, 'tables/order_detail.html', context)