from django import forms
from .models import Configuracion
from tables.models import CostoAdicional

# 1. FORMULARIO DE IDENTIDAD
class ConfigIdentidadForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        fields = ['nombre_empresa', 'rif', 'direccion', 'telefono', 'pm_banco', 'pm_telefono', 'pm_cedula']
        widgets = {
            'direccion': forms.Textarea(attrs={'rows': 3}),
            'pm_banco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Banesco (0134)'}),
            'pm_telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 04141234567'}),
            'pm_cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: V12345678'}),
        }

# 3. FORMULARIO VISUAL Y TÉCNICO (AQUÍ AGREGUÉ LA CONFIGURACIÓN DE IMPRESIÓN)
class ConfigVisualForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        # Agregamos: impresora_ticket, ancho_papel, auto_imprimir, usar_logo_impresora, abrir_caja_registradora
        fields = ['logo', 'mensaje_ticket', 'impresora_ticket', 'ancho_papel', 'auto_imprimir', 'usar_logo_impresora', 'abrir_caja_registradora']

        
        widgets = {
            'mensaje_ticket': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mensaje al pie del ticket'}),
            'impresora_ticket': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre exacto de la impresora'}),
            'ancho_papel': forms.NumberInput(attrs={'class': 'form-control'}),
            'auto_imprimir': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}),
            'usar_logo_impresora': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}),
            'abrir_caja_registradora': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}),
        }
        labels = {
            'impresora_ticket': 'Nombre de Impresora (PC)',
            'ancho_papel': 'Ancho del Papel (mm)',
            'auto_imprimir': '¿Imprimir Automáticamente?',
            'usar_logo_impresora': '¿Imprimir logo en ticket?',
            'abrir_caja_registradora': '¿Abrir Gaveta de Dinero?'
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

class ConfigProcesosForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        fields = [
            'tasa_dolar',
            'usar_scraping_bcv',
            'enviar_alerta_stock_correo',
            'correo_destino_alertas',
            'codigo_producto_automatico',
            'caja_individual',
            'caja_mediana',
            'caja_familiar'
        ]
        labels = {
            'tasa_dolar': 'Tasa del Dólar (Manual/Fallback)',
            'usar_scraping_bcv': '¿Actualizar Tasa BCV automáticamente?',
            'enviar_alerta_stock_correo': '¿Enviar alerta de stock por correo?',
            'correo_destino_alertas': 'Correo Destino de Alertas',
            'codigo_producto_automatico': '¿Código de producto automático?',
            'caja_individual': 'Caja / Empaque para Pizzas Individuales',
            'caja_mediana': 'Caja / Empaque para Pizzas Medianas',
            'caja_familiar': 'Caja / Empaque para Pizzas Familiares',
        }
        widgets = {
            'tasa_dolar': forms.NumberInput(attrs={'class': 'form-control-card', 'step': '0.01'}),
            'usar_scraping_bcv': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}),
            'enviar_alerta_stock_correo': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}),
            'correo_destino_alertas': forms.EmailInput(attrs={'class': 'form-control-card', 'placeholder': 'ejemplo@correo.com'}),
            'codigo_producto_automatico': forms.CheckboxInput(attrs={'class': 'form-check-input', 'style': 'width: 20px; height: 20px;'}),
            'caja_individual': forms.Select(attrs={'class': 'form-control-card'}),
            'caja_mediana': forms.Select(attrs={'class': 'form-control-card'}),
            'caja_familiar': forms.Select(attrs={'class': 'form-control-card'}),
        }