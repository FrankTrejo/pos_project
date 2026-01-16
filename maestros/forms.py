from django import forms
from inventory.models import Insumo

class MaestroInsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        # Aquí pedimos TODO lo necesario para una compra
        fields = ['nombre', 'categoria', 'unidad', 'stock_minimo', 'precio_mercado', 'peso_standar', 'merma_porcentaje']
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Harina de Trigo'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'unidad': forms.Select(attrs={'class': 'form-select'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control'}),
            
            # Campos de compra OBLIGATORIOS visualmente
            'precio_mercado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Costo $'}),
            'peso_standar': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': 'Peso del empaque'}),
            'merma_porcentaje': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        # Forzamos a que NO sea compuesto (porque es Materia Prima del Maestro)
        cleaned_data['es_insumo_compuesto'] = False 
        
        # Validamos que pongan precio y peso
        precio = cleaned_data.get('precio_mercado')
        peso = cleaned_data.get('peso_standar')
        
        if not precio:
            self.add_error('precio_mercado', 'El Maestro requiere el costo de compra.')
        if not peso:
            self.add_error('peso_standar', 'El Maestro requiere el peso del empaque.')
            
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.es_insumo_compuesto = False # Aseguramos en BD
        if commit:
            instance.save()
        return instance