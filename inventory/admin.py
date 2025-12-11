from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import UnidadMedida, CategoriaInsumo, Insumo, MovimientoInventario

class InsumoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'stock_actual', 'unidad', 'costo_unitario', 'stock_minimo')
    list_filter = ('categoria',)
    search_fields = ('nombre',)

class MovimientoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'tipo', 'insumo', 'cantidad', 'costo_unitario_movimiento', 'usuario')
    list_filter = ('tipo', 'fecha')
    ordering = ('-fecha',)

admin.site.register(UnidadMedida)
admin.site.register(CategoriaInsumo)
admin.site.register(Insumo, InsumoAdmin)
admin.site.register(MovimientoInventario, MovimientoAdmin)