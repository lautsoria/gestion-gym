from django import forms
from .models import Producto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'precio', 'stock']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control bg-dark text-white border-secondary', 'placeholder': 'Ej: Agua 500ml'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control bg-dark text-white border-secondary'}),
        }
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        # Si estamos editando, self.instance.pk tendrá el ID del producto actual
        # Buscamos productos con el mismo nombre pero con un ID DIFERENTE al actual
        exists = Producto.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk).exists()
        
        if exists:
            raise forms.ValidationError("Ya existe otro producto con este nombre.")
        return nombre