from django import forms
from .models import Producto, IngredienteProducto, CostoAsignadoProducto, CostoAdicional
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
# tables/forms.py

class ProductoPriceForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['precio']
        widgets = {
            'precio': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'id': 'input-precio'}),
        }

    # --- NUEVA VALIDACIÓN ---
    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        
        # Si el precio es None, 0 o negativo, lanzamos error
        if precio is None or precio <= 0:
            raise forms.ValidationError("El precio de venta debe ser mayor a 0 para finalizar.")
        
        return precio

class CostoAdicionalForm(forms.ModelForm):
    class Meta:
        model = CostoAsignadoProducto
        fields = ['costo_adicional', 'valor_aplicado']
        widgets = {
            'costo_adicional': forms.Select(attrs={'class': 'form-input', 'id': 'select-costo-master'}),
            # CAMBIO AQUÍ: Usamos TextInput y inputmode="decimal"
            'valor_aplicado': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': '0,00',
                'inputmode': 'decimal' # Activa teclado numérico en móviles
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['costo_adicional'].queryset = CostoAdicional.objects.all()
        self.fields['costo_adicional'].empty_label = "Seleccione un costo..."