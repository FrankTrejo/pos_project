from django import forms
from .models import Configuracion
from tables.models import CostoAdicional

# 1. FORMULARIO DE IDENTIDAD
class ConfigIdentidadForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        fields = ['nombre_empresa', 'rif', 'direccion', 'telefono']
        widgets = {
            'direccion': forms.Textarea(attrs={'rows': 3}),
        }

# 2. FORMULARIO DE ECONOMÍA (CORREGIDO)
class ConfigEconomiaForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        # AQUI ESTABA EL ERROR: Ahora usamos los nombres reales de tu models.py
        fields = [
            'tasa_dolar',           # Antes decía tasa_cambio
            'iva_porcentaje',       # Antes decía iva
            'igtf_porcentaje',      # Antes decía igtf
            'servicio_porcentaje',
            'monto_delivery_fijo',
            'costo_caja_pequena',
            'costo_caja_grande',
            'gastos_operativos_porcentaje'
        ]
        # Etiquetas para que se vea bonito en la pantalla
        labels = {
            'tasa_dolar': 'Tasa del Dólar (BCV)',
            'iva_porcentaje': 'IVA (%)',
            'igtf_porcentaje': 'IGTF (%)',
            'servicio_porcentaje': 'Propina / Servicio (%)',
            'monto_delivery_fijo': 'Costo Delivery ($)',
            'costo_caja_pequena': 'Costo Caja Pequeña ($)',
            'costo_caja_grande': 'Costo Caja Grande ($)',
        }

# 3. FORMULARIO VISUAL
class ConfigVisualForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        fields = ['logo', 'mensaje_ticket']

class CostoAdicionalForm(forms.ModelForm):
    class Meta:
        model = CostoAdicional
        fields = ['nombre', 'tipo', 'valor_defecto']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Caja Mediana, Gas...'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'valor_defecto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {
            'valor_defecto': 'Valor ($ o %)'
        }