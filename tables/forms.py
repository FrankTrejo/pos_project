from django import forms
from .models import Producto, IngredienteProducto
from inventory.models import Insumo

# PASO 1: SOLO DATOS BÁSICOS
class ProductoBasicForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'tamano'] # Quitamos precio
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Pizza Margarita'}),
            'categoria': forms.Select(attrs={'class': 'form-input'}),
            'tamano': forms.Select(attrs={'class': 'form-input'}),
        }

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'precio', 'tamano']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ej: Pizza Margarita'}),
            'categoria': forms.Select(attrs={'class': 'form-input'}),
            'precio': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'tamano': forms.Select(attrs={'class': 'form-input'}),
        }

# PASO 2: (Usamos el IngredienteForm que ya tienes, no cambia)
class IngredienteForm(forms.ModelForm):
    class Meta:
        model = IngredienteProducto
        fields = ['insumo', 'cantidad']
        widgets = {
            'insumo': forms.Select(attrs={'class': 'form-input'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.001', 'placeholder': 'Cantidad'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['insumo'].queryset = Insumo.objects.all().order_by('nombre')
        self.fields['insumo'].label_from_instance = lambda obj: f"{obj.nombre} ({obj.unidad.codigo}) - ${obj.costo_unitario:.2f}"

# PASO 3: CONFIGURACIÓN DE PRECIO
class ProductoPriceForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['precio'] # Solo precio
        widgets = {
            'precio': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'id': 'input-precio'}),
        }