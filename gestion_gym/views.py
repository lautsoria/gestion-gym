from django.shortcuts import render
from .models import Clase
from django.db.models import Sum
from .models import Pago
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages # Importamos el sistema de mensajes
from .models import Inscripcion
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.admin.views.decorators import staff_member_required
from .forms import RegistroCompletoForm 



class RegistroUsuario(generic.CreateView):
    form_class = RegistroCompletoForm 
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'




def es_admin(user):
    return user.is_superuser

def ver_horarios(request):
    ahora = timezone.now()
    lista_de_clases = Clase.objects.filter(horario__gte=ahora).order_by('horario')
    return render(request, 'gestion_gym/horarios.html', {'lista_de_clases': lista_de_clases})



@staff_member_required
def reporte_ganancias(request):
    ahora = timezone.now()
    pagos_mes = Pago.objects.filter(fecha_pago__year=ahora.year, fecha_pago__month=ahora.month)
    
    # Cálculos por método
    efectivo = pagos_mes.filter(metodo='EFECTIVO').aggregate(Sum('monto'))['monto__sum'] or 0
    transferencia = pagos_mes.filter(metodo='TRANSFERENCIA').aggregate(Sum('monto'))['monto__sum'] or 0
    otros = pagos_mes.exclude(metodo__in=['EFECTIVO', 'TRANSFERENCIA']).aggregate(Sum('monto'))['monto__sum'] or 0
    
    total_mensual = efectivo + transferencia + otros

    contexto = {
        'total_mensual': total_mensual,
        'efectivo': efectivo,
        'transferencia': transferencia,
        'otros': otros,
        'cantidad_pagos': pagos_mes.count(),
        'mes_nombre': ahora.strftime('%B %Y')
    }
    return render(request, 'gestion_gym/reporte.html', contexto)





@login_required
def inscribir_clase(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    
    # 1. Verificar si el usuario YA está anotado
    ya_anotado = Inscripcion.objects.filter(usuario=request.user, clase=clase).exists()
    
    if ya_anotado:
        messages.warning(request, f"Ya estás anotado en la clase de {clase.nombre_actividad}.")
    
    # 2. Si no está anotado, verificar cupo
    elif clase.capacidad_maxima > 0:
        # Creamos la inscripción
        Inscripcion.objects.create(usuario=request.user, clase=clase)
        
        # Restamos el cupo
        clase.capacidad_maxima -= 1
        clase.save()
        
        messages.success(request, f"¡Te has anotado con éxito a {clase.nombre_actividad}!")
    
    else:
        messages.error(request, "Lo sentimos, ya no quedan cupos para esta clase.")
        
    return redirect('horarios_gym')





@login_required
def mis_clases(request):
    ahora = timezone.now()
    mis_reservas = Inscripcion.objects.filter(
        usuario=request.user, 
        clase__horario__gte=ahora 
    ).select_related('clase')
    
    return render(request, 'gestion_gym/mis_clases.html', {'reservas': mis_reservas})

@login_required
def cancelar_reserva(request, inscripcion_id):
    # Buscamos la inscripción, asegurándonos de que pertenezca al usuario (seguridad)
    reserva = get_object_or_404(Inscripcion, id=inscripcion_id, usuario=request.user)
    
    # Devolvemos el cupo a la clase
    clase = reserva.clase
    clase.capacidad_maxima += 1
    clase.save()
    
    # Borramos la inscripción
    reserva.delete()
    
    messages.info(request, f"Has cancelado tu lugar en {clase.nombre_actividad}.")
    return redirect('mis_clases')



@staff_member_required
def lista_clases_admin(request):
    # Mostramos todas las clases para que el admin elija cuál ver
    clases = Clase.objects.all().order_by('horario')
    return render(request, 'gestion_gym/admin_clases.html', {'clases': clases})

@staff_member_required
def detalle_asistencia(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    # Buscamos todas las inscripciones de ESTA clase
    anotados = Inscripcion.objects.filter(clase=clase).select_related('usuario')
    
    return render(request, 'gestion_gym/detalle_asistencia.html', {
        'clase': clase,
        'anotados': anotados
    })