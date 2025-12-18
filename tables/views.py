# tables/views.py (CÓDIGO COMPLETO Y CORREGIDO)

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Max
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
import json
from .models import CostoAdicional, CostoAsignadoProducto # Importar modelos nuevos
from .forms import CostoAdicionalForm # Importar form nuevo


# Tus modelos y formularios
from .models import Table, Categoria, Producto, TasaBCV, IngredienteProducto
from .forms import ProductoBasicForm, RecetaProductoForm, ProductoPriceForm
from .scrapping import obtener_tasa_bcv

# ==========================================
#  LÓGICA ORIGINAL (MESAS Y POS)
# ==========================================

def initialize_tables_if_empty():
    if Table.objects.count() == 0:
        tables_to_create = []
        for i in range(1, 21):
            tables_to_create.append(Table(number=i))
        Table.objects.bulk_create(tables_to_create)

def index(request):
    initialize_tables_if_empty()
    tables = Table.objects.all()
    return render(request, 'tables/index.html', {'tables': tables})

def create_table(request):
    max_number = Table.objects.aggregate(Max('number'))['number__max']
    new_number = (max_number or 0) + 1
    Table.objects.create(number=new_number)
    return redirect('index')

def toggle_status(request, table_id):
    if request.method == 'POST':
        table = get_object_or_404(Table, id=table_id)
        table.is_occupied = not table.is_occupied
        # Si se libera la mesa, quitamos al mesero
        if not table.is_occupied:
            table.mesero = None
        table.save()
        return JsonResponse({'is_occupied': table.is_occupied})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def asignar_mesero(request, table_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            table = Table.objects.get(id=table_id)
            if user_id:
                user = User.objects.get(id=user_id)
                table.mesero = user
                nombre = user.username
            else:
                table.mesero = None
                nombre = ""
            table.save()
            return JsonResponse({'status': 'ok', 'mesero': nombre})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=400)

def table_order_view(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    tasa_actual_texto = obtener_tasa_bcv()
    
    tasa_obj = TasaBCV.objects.order_by('-fecha_actualizacion').first()
    tasa_numerica = float(tasa_obj.precio) if tasa_obj else 0

    categorias = Categoria.objects.all()
    productos = Producto.objects.filter(precio__gt=0).select_related('categoria')
    
    meseros = User.objects.filter(is_active=True)

    context = {
        'table': table,
        'tasa_cambio': tasa_actual_texto,
        'tasa_valor': tasa_numerica,
        'categorias': categorias,
        'productos': productos,
        'meseros': meseros,
    }
    return render(request, 'tables/order_detail.html', context)


# ==========================================
#  NUEVA LÓGICA (PRODUCTOS Y RECETAS)
# ==========================================

# 1. CATÁLOGO DE PRODUCTOS
@staff_member_required
def product_list(request):
    productos = Producto.objects.all().order_by('nombre')
    return render(request, 'products/product_list.html', {'productos': productos})

# 2. PASO 1: CREAR DATOS BÁSICOS
@staff_member_required
def product_create(request, pk=None):
    if pk:
        producto = get_object_or_404(Producto, pk=pk)
        titulo = "Editar Datos Básicos"
    else:
        producto = None
        titulo = "Paso 1: Crear Producto"

    if request.method == 'POST':
        form = ProductoBasicForm(request.POST, instance=producto)
        if form.is_valid():
            prod = form.save(commit=False)
            if not pk:
                prod.precio = 0 # Precio temporal
            prod.save()
            messages.success(request, "Datos básicos guardados.")
            return redirect('recipe_manager', pk=prod.pk)
    else:
        form = ProductoBasicForm(instance=producto)

    return render(request, 'products/product_form.html', {'form': form, 'titulo': titulo})

# 3. PASO 2: GESTOR DE RECETAS
@staff_member_required
def recipe_manager(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        if 'delete_ingrediente' in request.POST:
            ing_id = request.POST.get('delete_ingrediente')
            IngredienteProducto.objects.filter(id=ing_id).delete()
            messages.warning(request, "Ingrediente eliminado.")
            return redirect('recipe_manager', pk=pk)
            
        form = RecetaProductoForm(request.POST)
        if form.is_valid():
            ingrediente = form.save(commit=False)
            ingrediente.producto = producto
            ingrediente.save()
            messages.success(request, "Ingrediente agregado.")
            return redirect('recipe_manager', pk=pk)
    else:
        form = RecetaProductoForm()

    context = {
        'producto': producto,
        'ingredientes': producto.ingredientes.all(),
        'form': form,
        'costo_total': producto.costo_receta,
    }
    return render(request, 'products/recipe_manager.html', context)

# 4. PASO 3: PRECIO FINAL
@staff_member_required
@staff_member_required
def product_pricing(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    # LÓGICA: AGREGAR O ELIMINAR COSTOS ADICIONALES
    if request.method == 'POST':
        
        # A) Eliminar un costo
        if 'delete_costo' in request.POST:
            cid = request.POST.get('delete_costo')
            CostoAsignadoProducto.objects.filter(id=cid).delete()
            messages.warning(request, "Costo adicional eliminado.")
            return redirect('product_pricing', pk=pk)
        
        # B) Agregar un costo nuevo (CON CORRECCIÓN DE COMAS)
        if 'add_costo' in request.POST:
            # 1. Creamos una copia editable de los datos recibidos
            datos_formulario = request.POST.copy()
            
            # 2. Limpieza manual de la coma en 'valor_aplicado'
            valor_sucio = datos_formulario.get('valor_aplicado', '')
            if ',' in valor_sucio:
                datos_formulario['valor_aplicado'] = valor_sucio.replace('.', '').replace(',', '.') # Quitamos punto de miles y cambiamos coma decimal
            
            # 3. Pasamos los datos ya limpios al formulario
            form_costo = CostoAdicionalForm(datos_formulario)
            
            if form_costo.is_valid():
                nuevo_costo = form_costo.save(commit=False)
                nuevo_costo.producto = producto
                nuevo_costo.save()
                messages.success(request, "Costo adicional agregado correctamente.")
                return redirect('product_pricing', pk=pk)
            else:
                # 4. Si falla, avisamos por qué (Esto es vital para depurar)
                messages.error(request, f"Error al agregar costo: {form_costo.errors}")

        # C) Guardar Precio Final (Formulario de precio)
        if 'save_price' in request.POST:
            datos_precio = request.POST.copy()
            # Limpieza también para el precio final
            precio_sucio = datos_precio.get('precio', '')
            if ',' in precio_sucio:
                 datos_precio['precio'] = precio_sucio.replace('.', '').replace(',', '.')
            
            form_precio = ProductoPriceForm(datos_precio, instance=producto)
            if form_precio.is_valid():
                form_precio.save()
                messages.success(request, f"¡Producto '{producto.nombre}' configurado exitosamente!")
                return redirect('product_list')
            else:
                 messages.error(request, f"Error en el precio: {form_precio.errors}")
    
    # Formularios vacíos para renderizar
    form_precio = ProductoPriceForm(instance=producto)
    form_costo = CostoAdicionalForm()

    context = {
        'producto': producto,
        'form_precio': form_precio,
        'form_costo': form_costo,
        'costo_receta': producto.costo_receta,
        'costos_adicionales': producto.costos_adicionales.all(),
        'total_indirectos': producto.costo_indirectos_total,
        'costo_total_final': producto.costo_total_real,
    }
    return render(request, 'products/product_pricing.html', context)
    producto = get_object_or_404(Producto, pk=pk)
    
    # LÓGICA: AGREGAR O ELIMINAR COSTOS ADICIONALES
    if request.method == 'POST':
        # A) Eliminar un costo
        if 'delete_costo' in request.POST:
            cid = request.POST.get('delete_costo')
            CostoAsignadoProducto.objects.filter(id=cid).delete()
            messages.warning(request, "Costo adicional eliminado.")
            return redirect('product_pricing', pk=pk)
        
        # B) Agregar un costo nuevo
        if 'add_costo' in request.POST:
            form_costo = CostoAdicionalForm(request.POST)
            if form_costo.is_valid():
                nuevo_costo = form_costo.save(commit=False)
                nuevo_costo.producto = producto
                nuevo_costo.save()
                messages.success(request, "Costo adicional agregado.")
                return redirect('product_pricing', pk=pk)

        # C) Guardar Precio Final (Formulario de precio)
        if 'save_price' in request.POST:
            form_precio = ProductoPriceForm(request.POST, instance=producto)
            if form_precio.is_valid():
                form_precio.save()
                messages.success(request, f"¡Producto '{producto.nombre}' configurado exitosamente!")
                return redirect('product_list')
    
    # Formularios vacíos para renderizar
    form_precio = ProductoPriceForm(instance=producto)
    form_costo = CostoAdicionalForm()

    context = {
        'producto': producto,
        'form_precio': form_precio,
        'form_costo': form_costo,
        # Datos calculados
        'costo_receta': producto.costo_receta,
        'costos_adicionales': producto.costos_adicionales.all(), # Lista de costos agregados
        'total_indirectos': producto.costo_indirectos_total,
        'costo_total_final': producto.costo_total_real, # La suma maestra
    }
    return render(request, 'products/product_pricing.html', context)

@staff_member_required
def product_delete(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        nombre = producto.nombre
        producto.delete()
        messages.success(request, f"Producto '{nombre}' eliminado correctamente.")
        
    return redirect('product_list')