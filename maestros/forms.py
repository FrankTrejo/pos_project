from django import forms
from inventory.models import Insumo

# maestros/forms.py

class MaestroInsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ['nombre', 'categoria', 'unidad', 'stock_minimo', 'precio_mercado', 'cantidad_por_precio', 'merma_porcentaje']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-input'}),
            'categoria': forms.Select(attrs={'class': 'form-input'}),
            'unidad': forms.Select(attrs={'class': 'form-input'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-input'}),
            'precio_mercado': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            
            # Nuevo campo visible
            'cantidad_por_precio': forms.NumberInput(attrs={'class': 'form-input', 'step': '1'}),
            
            'merma_porcentaje': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1'}),
        }