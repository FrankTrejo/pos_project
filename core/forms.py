from django import forms
from .models import Configuracion

class ConfiguracionForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        fields = '__all__'
        widgets = {
            'direccion': forms.Textarea(attrs={'rows': 2}),
            'mensaje_ticket': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dar estilo a todos los campos
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})