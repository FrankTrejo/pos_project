from django import forms
from .models import Insumo, IngredienteCompuesto, MovimientoInventario

# 1. FORMULARIO PARA CREAR EL INSUMO (Datos Básicos)
class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ['nombre', 'categoria', 'unidad', 'stock_minimo', 'es_insumo_compuesto']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'categoria': forms.Select(attrs={'class': 'form-input'}),
            'unidad': forms.Select(attrs={'class': 'form-input'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}), # Se habilitará solo si NO es compuesto
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