# staff/forms.py
from django import forms
from django.contrib.auth.models import User, Group

class PersonalForm(forms.ModelForm):
    # Campos extra que no están directamente en el modelo User de forma simple
    rol = forms.ModelChoiceField(
        queryset=Group.objects.all(), 
        required=True, 
        label="Rol / Cargo",
        empty_label="Seleccione un cargo"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False, 
        label="Contraseña",
        help_text="Dejar en blanco si no desea cambiarla (solo edición)"
    )
    first_name = forms.CharField(required=True, label="Nombre")
    last_name = forms.CharField(required=True, label="Apellido")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        labels = {
            'username': 'Usuario (Login)',
            'email': 'Correo Electrónico',
            'is_active': '¿Está Activo?'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si estamos editando, pre-cargamos el rol actual
        if self.instance.pk:
            current_group = self.instance.groups.first()
            if current_group:
                self.fields['rol'].initial = current_group

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # 1. Guardar Contraseña solo si se escribió algo
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        
        if commit:
            user.save()
            # 2. Asignar Grupo (Rol)
            user.groups.clear() # Limpiamos grupos anteriores
            grupo_seleccionado = self.cleaned_data.get('rol')
            if grupo_seleccionado:
                user.groups.add(grupo_seleccionado)
                
            # Si es admin, le damos permisos de staff para entrar al admin de Django si se desea
            if grupo_seleccionado.name == 'Administrador':
                user.is_staff = True
                user.is_superuser = True # Opcional: Cuidado con esto
                user.save()
            else:
                user.is_staff = False
                user.is_superuser = False
                user.save()
                
        return user