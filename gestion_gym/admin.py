from django.contrib import admin
from .models import Clase, Pago, Inscripcion
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Pago,Perfil
from django.utils import timezone
from django.utils.html import format_html
from django.contrib.auth.models import Group



# gestion_gym/admin.py
@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ('nombre_actividad', 'instructor', 'horario', 'capacidad_maxima')
    # Esto te crea un buscador y filtros por fecha a la derecha:
    search_fields = ('nombre_actividad', 'instructor')
    list_filter = ('horario', 'nombre_actividad') 
    date_hierarchy = 'horario' # Agrega una barrita de navegación por fechas arriba

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
    


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'clases_disponibles', 'fecha_vencimiento', 'telefono')
    list_editable = ('clases_disponibles', 'fecha_vencimiento')
    
class UserGymAdmin(BaseUserAdmin):
    # Dejamos solo los cupos y la fecha del último pago
    list_display = BaseUserAdmin.list_display + ('cupos_restantes','vencimiento', 'ultimo_pago_fecha')
    def vencimiento(self, obj):
        try:
            return obj.perfil.fecha_vencimiento
        except:
            return "N/A"
    vencimiento.short_description = "Vence el"

    def cupos_restantes(self, obj):
        try:
            cupos = obj.perfil.clases_disponibles
            # Si le quedan 2 o menos, lo ponemos en rojo para avisar
            if cupos <= 2:
                return format_html('<span style="color: #e74c3c; font-weight: bold;">{} (Recargar)</span>', cupos)
            return format_html('<span style="color: #2ecc71; font-weight: bold;">{}</span>', cupos)
        except:
            return 0
    cupos_restantes.short_description = "Clases Disponibles"

    def ultimo_pago_fecha(self, obj):
        ultimo = Pago.objects.filter(usuario=obj).order_by('-fecha_pago').first()
        if ultimo:
            return ultimo.fecha_pago
        return "Sin registros"
    ultimo_pago_fecha.short_description = "Último Pago"

# No olvides estas líneas para que el cambio se aplique
admin.site.unregister(User)
admin.site.register(User, UserGymAdmin)

admin.site.unregister(Group)