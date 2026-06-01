from django import forms
from inventory.models import Insumo

class MaestroInsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        # Aquí pedimos TODO lo necesario para una compra
        fields = ['nombre', 'categoria', 'unidad', 'stock_minimo', 'precio_mercado', 'peso_standar', 'merma_porcentaje', 'es_extra']
        # ======================================================================
        # --- NUEVO: Interceptar y limpiar los valores al cargar el formulario ---
        # ======================================================================
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
            # Solo aplicamos la limpieza si estamos editando una instancia que ya existe
            if self.instance and self.instance.pk:
                campos_numericos = ['precio_mercado', 'peso_standar', 'stock_minimo', 'merma_porcentaje']
                
                for campo in campos_numericos:
                    valor = getattr(self.instance, campo)
                    if valor is not None:
                        valor_float = float(valor)
                        # Si es un número exacto (ej: 14.00), lo inyectamos como entero (14)
                        # Si tiene decimales (ej: 14.50), lo inyectamos limpio (14.5)
                        self.initial[campo] = int(valor_float) if valor_float.is_integer() else valor_float
        # ======================================================================
        
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

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre:
            # Buscamos de forma insensible a mayúsculas/minúsculas si el nombre existe
            qs = Insumo.objects.filter(nombre__iexact=nombre)
            # Si estamos editando, excluimos de la búsqueda al propio insumo que estamos guardando
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Ya existe un concepto registrado con este nombre.")
        return nombre

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