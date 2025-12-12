from django.contrib import admin
from .models import Table, Categoria, Producto, TasaBCV, IngredienteProducto

# --- INLINE DE INGREDIENTES ---
class IngredienteInline(admin.TabularInline):
    model = IngredienteProducto
    extra = 1
    autocomplete_fields = ['insumo'] 
    
    # Mostramos columnas informativas (Solo lectura)
    readonly_fields = ('costo_unitario_insumo', 'subtotal_costo')
    
    # Campos que SÍ se pueden editar
    fields = ('insumo', 'cantidad', 'costo_unitario_insumo', 'subtotal_costo')

    def costo_unitario_insumo(self, obj):
        # Muestra cuánto cuesta 1 unidad de ese insumo hoy
        if obj.insumo:
            return f"${obj.insumo.costo_unitario:.2f} / {obj.insumo.unidad.codigo}"
        return "-"
    costo_unitario_insumo.short_description = "Costo Insumo (Hoy)"

    def subtotal_costo(self, obj):
        # Muestra cuánto cuesta la cantidad que estás usando (Ej: 0.200kg * Precio)
        if obj.insumo and obj.cantidad:
            total = obj.cantidad * obj.insumo.costo_unitario
            return f"${total:.2f}"
        return "$0.00"
    subtotal_costo.short_description = "Costo Ingrediente"


# --- ADMIN DEL PRODUCTO PRINCIPAL ---
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # Esto organiza el formulario en secciones bonitas
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'categoria', 'tamano')
        }),
        ('Análisis Financiero (Calculado)', {
            'fields': ('ver_costo_receta', 'precio', 'ver_ganancia'),
            'description': 'Agregue los ingredientes abajo y presione "Guardar y continuar" para actualizar estos cálculos.'
        }),
    )

    inlines = [IngredienteInline]
    
    # Campos que el usuario NO puede editar (porque son cálculos)
    readonly_fields = ('ver_costo_receta', 'ver_ganancia')

    list_display = ('nombre', 'tamano', 'precio', 'ver_costo_receta', 'ver_ganancia_lista')
    list_filter = ('categoria', 'tamano')
    search_fields = ('nombre',)

    # --- FUNCIONES PARA MOSTRAR DATOS CALCULADOS ---
    
    def ver_costo_receta(self, obj):
        # Esto muestra el costo en el formulario de edición
        return f"${obj.costo_receta:.2f}"
    ver_costo_receta.short_description = "COSTO REAL (Suma de Ingredientes)"

    def ver_ganancia(self, obj):
        ganancia = obj.ganancia_estimada
        margen = obj.margen_ganancia
        style = "color: green; font-weight: bold;" if ganancia > 0 else "color: red; font-weight: bold;"
        
        # Inyectamos un poco de HTML para que se vea verde o rojo
        from django.utils.html import format_html
        return format_html(
            '<span style="{}">${:.2f} (Margen: {:.1f}%)</span>',
            style, ganancia, margen
        )
    ver_ganancia.short_description = "Ganancia Estimada"

    # Versión simple para la lista azul de productos
    def ver_ganancia_lista(self, obj):
        return f"${obj.ganancia_estimada:.2f}"
    ver_ganancia_lista.short_description = "Ganancia"

# Registros simples
admin.site.register(Table)
admin.site.register(Categoria)
admin.site.register(TasaBCV)