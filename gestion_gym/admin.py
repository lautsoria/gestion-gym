from django.contrib import admin
from .models import Clase, Pago, Inscripcion

# Configuración personalizada para Clases
@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ('nombre_actividad', 'instructor', 'horario', 'capacidad_maxima')
    list_filter = ('nombre_actividad', 'horario')
    search_fields = ('instructor',)

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    # Agregamos 'metodo' a la vista de lista
    list_display = ('usuario', 'monto', 'metodo', 'fecha_pago')
    # Añadimos el filtro lateral por método
    list_filter = ('metodo', 'fecha_pago')
    search_fields = ('usuario__username', 'usuario__first_name')  
# Configuración para Inscripciones
@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'clase', 'fecha_reserva')
    list_filter = ('clase', 'fecha_reserva')

