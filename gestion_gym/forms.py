from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Clase


class RegistroCompletoForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", required=True)
    last_name = forms.CharField(label="Apellido", required=True)
    email = forms.EmailField(label="Correo Electrónico", required=True)
    telefono = forms.CharField(max_length=20, label="Celular / WhatsApp")
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email','telefono')



class ClaseForm(forms.ModelForm):
    class Meta:
        model = Clase
        fields = ['nombre_actividad', 'instructor', 'horario', 'capacidad_maxima']
        widgets = {
            'nombre_actividad': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
            'instructor': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
            'horario': forms.DateTimeInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'type': 'datetime-local'}),
            'capacidad_maxima': forms.NumberInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
        }