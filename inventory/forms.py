from django import forms
from .models import Insumo, IngredienteCompuesto, MovimientoInventario

from django import forms
from .models import Insumo

# Formulario LIGERO solo para crear Recetas (Sin precios de compra)
class RecetaInsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        # Solo pedimos datos básicos. El precio y peso se calculan solos luego.
        fields = ['nombre', 'categoria', 'unidad', 'stock_minimo']
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Salsa Napolitana'}),
            'categoria': forms.Select(attrs={'class': 'form-input'}),
            'unidad': forms.Select(attrs={'class': 'form-input'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-input'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Aquí forzamos a que SI SEA COMPUESTO
        instance.es_insumo_compuesto = True
        # Ponemos valores dummy en compra para que no falle la BD
        instance.precio_mercado = 0
        instance.peso_standar = 1 
        instance.costo_unitario = 0 # Se calculará al agregar ingredientes
        
        if commit:
            instance.save()
        return instance

class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        # AQUI AGREGAMOS 'peso_standar' y 'precio_mercado'
        fields = ['nombre', 'categoria', 'unidad', 'stock_minimo', 'precio_mercado', 'peso_standar', 'merma_porcentaje', 'es_insumo_compuesto']
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'categoria': forms.Select(attrs={'class': 'form-input'}),
            'unidad': forms.Select(attrs={'class': 'form-input'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-input'}),
            
            # NUEVOS CAMPOS CONFIGURADOS
            'precio_mercado': forms.NumberInput(attrs={
                'class': 'form-input', 
                'step': '0.01',
                'placeholder': 'Costo total de compra ($)'
            }),
            'peso_standar': forms.NumberInput(attrs={
                'class': 'form-input', 
                'step': '0.001',
                'placeholder': '¿Cuánto trae el saco/paquete? (Gr/Ml)'
            }),
            
            'merma_porcentaje': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1'}),
            'es_insumo_compuesto': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'check-compuesto'}),
        }
# 2. FORMULARIO PARA AGREGAR INGREDIENTES A UN COMPUESTO
class ComponenteForm(forms.ModelForm):
    class Meta:
        model = IngredienteCompuesto
        fields = ['insumo_hijo', 'cantidad']
        widgets = {
            'insumo_hijo': forms.Select(attrs={'class': 'form-input'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.001'}),
        }
    
    def __init__(self, *args, **kwargs):
        # Excluir insumos compuestos para evitar ciclos infinitos (Masa dentro de Masa) por seguridad básica
        super().__init__(*args, **kwargs)
        self.fields['insumo_hijo'].queryset = Insumo.objects.all().order_by('nombre')

from django import forms
from .models import Insumo, MovimientoInventario, UnidadMedida

class MovimientoInventarioForm(forms.ModelForm):
    class Meta:
        model = MovimientoInventario
        fields = ['insumo', 'tipo', 'cantidad', 'unidad_movimiento', 'costo_unitario_movimiento', 'nota']
        widgets = {
            'insumo': forms.Select(attrs={'class': 'form-input'}),
            'tipo': forms.Select(attrs={'class': 'form-input'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Ej: 1 (Saco)'}),
            'unidad_movimiento': forms.Select(attrs={'class': 'form-input'}), # Aquí seleccionas KG
            'costo_unitario_movimiento': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Precio total del saco o kilo'}),
            'nota': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Por defecto seleccionamos Kilogramo si existe, para facilitar la vida
        try:
            kg_unit = UnidadMedida.objects.filter(codigo__iexact='kg').first()
            if kg_unit:
                self.fields['unidad_movimiento'].initial = kg_unit
        except:
            pass

class ProduccionForm(forms.Form):
    cantidad_lotes = forms.IntegerField(
        label="¿Cuántas tandas/lotes preparaste?",
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input', 
            'placeholder': 'Ej: 1 para un lote normal',
            'style': 'font-size: 1.2em; font-weight: bold; text-align: center;'
        })
    )
    nota = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Opcional: Nota de referencia'})
    )