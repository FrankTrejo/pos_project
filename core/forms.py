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

# 2. FORMULARIO DE ECONOMÍA
class ConfigEconomiaForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        fields = [
            'tasa_dolar',           
            'iva_porcentaje',       
            'igtf_porcentaje',      
            'servicio_porcentaje',
            'monto_delivery_fijo',
            'costo_caja_pequena',
            'costo_caja_grande',
            'gastos_operativos_porcentaje'
        ]
        labels = {
            'tasa_dolar': 'Tasa del Dólar (BCV)',
            'iva_porcentaje': 'IVA (%)',
            'igtf_porcentaje': 'IGTF (%)',
            'servicio_porcentaje': 'Propina / Servicio (%)',
            'monto_delivery_fijo': 'Costo Delivery ($)',
            'costo_caja_pequena': 'Costo Caja Pequeña ($)',
            'costo_caja_grande': 'Costo Caja Grande ($)',
        }

# 3. FORMULARIO VISUAL Y TÉCNICO (AQUÍ AGREGUÉ LA CONFIGURACIÓN DE IMPRESIÓN)
class ConfigVisualForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        # Agregamos: impresora_ticket, ancho_papel, auto_imprimir
        fields = ['logo', 'mensaje_ticket', 'impresora_ticket', 'ancho_papel', 'auto_imprimir']
        
        widgets = {
            'mensaje_ticket': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mensaje al pie del ticket'}),
            'impresora_ticket': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre exacto de la impresora'}),
            'ancho_papel': forms.NumberInput(attrs={'class': 'form-control'}),
            'auto_imprimir': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}),
        }
        labels = {
            'impresora_ticket': 'Nombre de Impresora (PC)',
            'ancho_papel': 'Ancho del Papel (mm)',
            'auto_imprimir': '¿Imprimir Automáticamente?'
        }

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