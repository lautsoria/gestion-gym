from django.shortcuts import render
from .models import Clase, Perfil
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
from django.contrib.auth.models import User



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

@staff_member_required
def reporte_ganancias(request):
    ahora = timezone.now()
    # 1. Seguimos calculando ingresos por mes para el balance financiero
    pagos_mes = Pago.objects.filter(fecha_pago__year=ahora.year, fecha_pago__month=ahora.month)
    
    efectivo = pagos_mes.filter(metodo='EFECTIVO').aggregate(Sum('monto'))['monto__sum'] or 0
    transferencia = pagos_mes.filter(metodo='TRANSFERENCIA').aggregate(Sum('monto'))['monto__sum'] or 0
    otros = pagos_mes.exclude(metodo__in=['EFECTIVO', 'TRANSFERENCIA']).aggregate(Sum('monto'))['monto__sum'] or 0
    
    total_mensual = efectivo + transferencia + otros

    # 2. NUEVA LÓGICA DE MOROSOS: Usuarios con saldo de clases negativo
    # Traemos los perfiles que deben clases y cargamos los datos del usuario para no hacer muchas consultas
    perfiles_deudores = Perfil.objects.filter(clases_disponibles__lt=0).select_related('usuario')
    
    morosos = []
    for p in perfiles_deudores:
        u = p.usuario
        u.clases_deuda = abs(p.clases_disponibles) # Convertimos -2 en 2 para mostrarlo bonito
        # Buscamos su último pago para saber hace cuánto no pone plata
        u.ultimo = Pago.objects.filter(usuario=u).order_by('-fecha_pago').first()
        morosos.append(u)

    contexto = {
        'total_mensual': total_mensual,
        'efectivo': efectivo,
        'transferencia': transferencia,
        'otros': otros,
        'cantidad_pagos': pagos_mes.count(),
        'mes_nombre': ahora.strftime('%B %Y'),
        'morosos': morosos,
        'cantidad_morosos': len(morosos),
    }
    return render(request, 'gestion_gym/reporte.html', contexto)





@login_required
def inscribir_clase(request, clase_id):
    # En lugar de request.user.perfil (que falla si no existe),
    # usamos get_or_create que asegura que el perfil EXISTA antes de seguir.
    perfil, created = Perfil.objects.get_or_create(usuario=request.user)
    
    # Limpiamos vencimientos (esto devuelve el objeto perfil actualizado)
    perfil = perfil.limpiar_vencidos()
    
    clase = get_object_or_404(Clase, id=clase_id)
    
    # Verificamos si ya está inscripto
    ya_inscripto = Inscripcion.objects.filter(usuario=request.user, clase=clase).exists()
    
    if not ya_inscripto:
        if clase.capacidad_maxima > 0:
            Inscripcion.objects.create(usuario=request.user, clase=clase)
            
            # Restamos cupo (permite negativos por tu nueva lógica)
            perfil.clases_disponibles -= 1
            perfil.save()
            
            # Restamos capacidad física de la clase
            clase.capacidad_maxima -= 1
            clase.save()
            
            messages.success(request, f"Inscripto con éxito en {clase.nombre_actividad}.")
        else:
            messages.error(request, "Lo sentimos, no hay más lugar físico en esta clase.")
    else:
        messages.warning(request, "Ya te encuentras anotado en esta clase.")
        
    return redirect('mis_clases')




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

@staff_member_required
def marcar_asistencia(request, inscripcion_id):
    # Buscamos la inscripción específica
    inscripcion = get_object_or_404(Inscripcion, id=inscripcion_id)
    
    # Cambiamos el estado (si era False pasa a True, y viceversa)
    inscripcion.asistio = not inscripcion.asistio
    inscripcion.save()
    
    # Redirigimos de vuelta a la lista de esa clase
    return redirect('asistencia', clase_id=inscripcion.clase.id)