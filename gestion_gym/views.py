from django.shortcuts import render
from django.db.models import Sum
from .models import Pago
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages # Importamos el sistema de mensajes
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.admin.views.decorators import staff_member_required
from .forms import RegistroCompletoForm 
from django.contrib.auth.models import User
from kiosco.models import Venta
from django.db import transaction
from .models import Clase, Inscripcion, Perfil


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
    
    # --- 1. DATOS DE CUOTAS (App gestion_gym) ---
    pagos_mes = Pago.objects.filter(fecha_pago__year=ahora.year, fecha_pago__month=ahora.month)
    cuotas_mensual = pagos_mes.aggregate(Sum('monto'))['monto__sum'] or 0
    cuotas_historico = Pago.objects.aggregate(Sum('monto'))['monto__sum'] or 0

    # --- 2. DATOS DE KIOSCO (App kiosco) ---
    ventas_mes = Venta.objects.filter(fecha__year=ahora.year, fecha__month=ahora.month)
    kiosco_mensual = ventas_mes.aggregate(Sum('total'))['total__sum'] or 0
    kiosco_historico = Venta.objects.aggregate(Sum('total'))['total__sum'] or 0

    # --- 3. UNIFICACIÓN DE VARIABLES ---
    # Sumamos ambos para que el HTML reciba el total final en la misma bolsa
    total_mensual = cuotas_mensual + kiosco_mensual
    total_historico = cuotas_historico + kiosco_historico

    # --- 4. DETALLE POR MÉTODO (Para el cuadrito de abajo) ---
    efectivo = pagos_mes.filter(metodo='EFECTIVO').aggregate(Sum('monto'))['monto__sum'] or 0
    transferencia = pagos_mes.filter(metodo='TRANSFERENCIA').aggregate(Sum('monto'))['monto__sum'] or 0
    otros = pagos_mes.exclude(metodo__in=['EFECTIVO', 'TRANSFERENCIA']).aggregate(Sum('monto'))['monto__sum'] or 0

    # --- 5. LÓGICA DE MOROSOS (Se mantiene igual) ---
    perfiles_deudores = Perfil.objects.filter(clases_disponibles__lt=0).select_related('usuario')
    morosos = []
    for p in perfiles_deudores:
        u = p.usuario
        u.clases_deuda = abs(p.clases_disponibles)
        u.ultimo = Pago.objects.filter(usuario=u).order_by('-fecha_pago').first()
        morosos.append(u)

    contexto = {
        'total_mensual': total_mensual,      
        'total_historico': total_historico,  
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
    # 1. SEGURIDAD: Solo permitimos inscripciones vía POST
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # select_for_update() bloquea la fila para que nadie más reserve 
                # ese último lugar mientras este código se ejecuta (Punto 4)
                clase = Clase.objects.select_for_update().get(id=clase_id)
                perfil, created = Perfil.objects.get_or_create(usuario=request.user)

                # 2. VALIDACIÓN: Evitar duplicados
                if Inscripcion.objects.filter(usuario=request.user, clase=clase).exists():
                    messages.warning(request, "Ya estás anotado en esta clase.")
                    return redirect('horarios')

                # 3. VALIDACIÓN: Cupos físicos (esto sí es estricto)
                if clase.capacidad_maxima <= 0:
                    messages.error(request, "¡Lo sentimos! Esta clase ya no tiene cupos disponibles.")
                    return redirect('horarios')

                # 4. LÓGICA DE NEGOCIO: Descontamos crédito y cupo
                # (Permitimos que clases_disponibles sea menor a 0)
                clase.capacidad_maxima -= 1
                clase.save()

                perfil.clases_disponibles -= 1
                perfil.save()

                Inscripcion.objects.create(usuario=request.user, clase=clase)
                
                messages.success(request, f"✅ Reserva confirmada para {clase.nombre_actividad}.")
                
        except Exception as e:
            messages.error(request, "Error al procesar la reserva.")
            
        return redirect('mis_clases')
    
    # Si intentan entrar por GET (URL), los mandamos a horarios
    return redirect('horarios')




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
    # 1. SEGURIDAD: Solo permitimos cancelar mediante una petición POST (desde el formulario)
    if request.method == 'POST':
        # Buscamos la reserva asegurándonos de que pertenezca al usuario logueado
        reserva = get_object_or_404(Inscripcion, id=inscripcion_id, usuario=request.user)
        
        try:
            # 2. TRANSACCIÓN: Se hace todo o no se hace nada
            with transaction.atomic():
                # Devolvemos el cupo a la clase
                clase = reserva.clase
                clase.capacidad_maxima += 1
                clase.save()
                
                # Devolvemos el crédito al perfil del usuario
                perfil = request.user.perfil
                perfil.clases_disponibles += 1
                perfil.save()
                
                # Borramos la inscripción definitivamente
                reserva.delete()
                
                messages.success(request, f"✅ Cancelación exitosa. Se te devolvió 1 crédito para {clase.nombre_actividad}.")
        except Exception as e:
            messages.error(request, "❌ Hubo un error al procesar la cancelación. Inténtalo de nuevo.")
            
        return redirect('mis_clases')
    
    # Si alguien intenta entrar por URL (GET), lo mandamos de vuelta sin hacer nada
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
    if request.method == 'POST': 
        inscripcion = get_object_or_404(Inscripcion, id=inscripcion_id)
        inscripcion.asistio = not inscripcion.asistio 
        inscripcion.save()
        return redirect('asistencia', clase_id=inscripcion.clase.id)
    return redirect('admin_clases') 

from django.contrib.auth.models import User
from django.http import HttpResponse

