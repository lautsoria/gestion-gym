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
from django.db import transaction,models
from django.db.models import Q
from .models import Clase, Inscripcion, Perfil,MovimientoCaja
from django.core.paginator import Paginator
from .forms import ClaseForm

class RegistroUsuario(generic.CreateView):
    form_class = RegistroCompletoForm 
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        # 1. Guardamos el usuario primero
        response = super().form_valid(form)
        user = self.object
        
        # 2. Guardamos el nombre y apellido en el objeto User
        user.first_name = form.cleaned_data.get('first_name')
        user.last_name = form.cleaned_data.get('last_name')
        user.email = form.cleaned_data.get('email')
        user.save()

        # 3. Guardamos el teléfono en el Perfil (que ya existe por el signal post_save)
        perfil = user.perfil
        perfil.telefono = form.cleaned_data.get('telefono')
        perfil.save()
        
        return response



def es_admin(user):
    return user.is_superuser

def ver_horarios(request):
    ahora = timezone.now()
    lista_de_clases = Clase.objects.filter(horario__gte=ahora).order_by('horario')
    return render(request, 'gestion_gym/horarios.html', {'lista_de_clases': lista_de_clases})



@staff_member_required
def reporte_ganancias(request):
    from django.utils import timezone
    import datetime

    # 1. Filtro de Fecha (Por defecto hoy)
    fecha_str = request.GET.get('fecha')
    if fecha_str:
        fecha_filtro = datetime.datetime.strptime(fecha_str, '%Y-%m-%d').date()
    else:
        fecha_filtro = timezone.now().date()

    # 2. Traer Clases de ese día específico
    clases = Clase.objects.filter(
        horario__date=fecha_filtro
    ).order_by('horario')

    # 3. Traer Morosos (Socios con 0 o menos cupos)
    morosos = User.objects.filter(
        perfil__clases_disponibles__lte=0, 
        is_staff=False
    ).select_related('perfil').order_by('first_name')

    context = {
        'clases': clases,
        'morosos': morosos,
        'fecha_filtro': fecha_filtro,
        'cantidad_morosos': morosos.count(),
    }
    return render(request, 'gestion_gym/reporte.html', context)



@staff_member_required
def crear_clase_rapida(request):
    if request.method == 'POST':
        form = ClaseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Clase creada correctamente.")
            return redirect('reporte_ganancias')
    else:
        # Pre-cargar la fecha si viene por URL (opcional)
        fecha_inicial = request.GET.get('fecha', None)
        form = ClaseForm()
        
    return render(request, 'recepcion/crear_clase.html', {'form': form})

@staff_member_required
def editar_clase_rapida(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    
    if request.method == 'POST':
        # Pasamos instance=clase para que Django sepa que es una edición y no una creación
        form = ClaseForm(request.POST, instance=clase)
        if form.is_valid():
            form.save()
            messages.success(request, f"✅ Clase '{clase.nombre_actividad}' actualizada.")
            return redirect('reporte_ganancias')
    else:
        # Cargamos el formulario con los datos actuales de la clase
        form = ClaseForm(instance=clase)
        
    return render(request, 'recepcion/editar_clase.html', {'form': form, 'clase': clase})

@staff_member_required
def eliminar_clase_rapida(request, clase_id):
    clase = get_object_or_404(Clase, id=clase_id)
    if request.method == 'POST':
        nombre = clase.nombre_actividad
        clase.delete()
        messages.warning(request, f"🗑️ Clase '{nombre}' eliminada.")
    return redirect('reporte_ganancias')




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
                perfil.limpiar_vencidos()

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




def gestion_usuarios_recepcion(request):
    query = request.GET.get('q')
    usuarios_list = User.objects.select_related('perfil').all().order_by('-id')

    if query:
        usuarios_list = usuarios_list.filter(
            Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query)
        )

    paginator = Paginator(usuarios_list, 20) # Mostramos de a 20
    page_number = request.GET.get('page')
    usuarios = paginator.get_page(page_number)
    
    return render(request, 'recepcion/lista_usuarios.html', {'usuarios': usuarios})

@staff_member_required
@transaction.atomic
def actualizar_cupos_pago(request, usuario_id):
    if request.method == 'POST':
        usuario = get_object_or_404(User, id=usuario_id)
        
        cantidad = int(request.POST.get('cupos_sumar', 0))
        monto_pagado = float(request.POST.get('monto', 0) or 0)
        metodo = request.POST.get('metodo', 'EFECTIVO')

        if cantidad > 0:
            # Al crear el Pago, el método save() del modelo
            # hará TODO el trabajo (Caja + Cupos + Vencimiento)
            Pago.objects.create(
                usuario=usuario,
                monto=monto_pagado,
                cantidad_clases=cantidad,
                metodo=metodo
            )
            messages.success(request, f"✅ Pago registrado correctamente para {usuario.first_name}.")
        else:
            messages.warning(request, "⚠️ La cantidad debe ser mayor a 0.")
            
        return redirect('recepcion')
    
@staff_member_required
@transaction.atomic
def registrar_movimiento(request):
    if request.method == 'POST':
        tipo = request.POST.get('tipo') # Recibe 'INGRESO' o 'EGRESO'
        monto = request.POST.get('monto')
        concepto = request.POST.get('concepto')
        metodo = request.POST.get('metodo')

        if monto and concepto:
            MovimientoCaja.objects.create(
                tipo=tipo,
                monto=float(monto),
                concepto=concepto,
                metodo=metodo
            )
            messages.success(request, f"✅ {tipo.capitalize()} registrado correctamente.")
        else:
            messages.error(request, "⚠️ Faltan datos obligatorios.")
            
    return redirect('caja_diaria') # Te devuelve a la planilla de caja
    

@staff_member_required
def caja_diaria(request):
    fecha_str = request.GET.get('fecha')
    if fecha_str:
        fecha_filtro = timezone.datetime.strptime(fecha_str, '%Y-%m-%d').date()
    else:
        fecha_filtro = timezone.now().date()

    # 1. Movimientos de Dinero (Ingresos y Egresos)
    movimientos = MovimientoCaja.objects.filter(fecha__date=fecha_filtro).order_by('fecha')
    ingresos = movimientos.filter(tipo='INGRESO')
    egresos = movimientos.filter(tipo='EGRESO')

    
    # 3. Totales
    total_ingresos = ingresos.aggregate(Sum('monto'))['monto__sum'] or 0
    total_egresos = egresos.aggregate(Sum('monto'))['monto__sum'] or 0
    saldo_neto = total_ingresos - total_egresos
    efectivo_dia = movimientos.filter(metodo='EFECTIVO', tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    transf_dia = movimientos.filter(metodo='TRANSFERENCIA', tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    tarjeta_dia = movimientos.filter(metodo='TARJETA', tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    efectivo_dia_salida = movimientos.filter(metodo='EFECTIVO', tipo='EGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    transf_dia_salida = movimientos.filter(metodo='TRANSFERENCIA', tipo='EGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    tarjeta_dia_salida = movimientos.filter(metodo='TARJETA', tipo='EGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    inicio_mes = fecha_filtro.replace(day=1)
    total_mensual = MovimientoCaja.objects.filter(
        tipo='INGRESO', 
        fecha__date__gte=inicio_mes, 
        fecha__date__lte=fecha_filtro
    ).aggregate(Sum('monto'))['monto__sum'] or 0

    total_egresos_mes = MovimientoCaja.objects.filter(
    tipo='EGRESO', 
    fecha__date__gte=inicio_mes, 
    fecha__date__lte=fecha_filtro
    ).aggregate(Sum('monto'))['monto__sum'] or 0

    context = {
        'ingresos': ingresos,
        'egresos': egresos,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'saldo_neto': saldo_neto,
        'fecha_filtro': fecha_filtro,
        'efectivo_dia': efectivo_dia-efectivo_dia_salida,
        'transf_dia': transf_dia-transf_dia_salida,
        'tarjeta_dia': tarjeta_dia-tarjeta_dia_salida,
        'mensual_dia': total_mensual-total_egresos_mes,
    }
    return render(request, 'recepcion/caja_diaria.html', context)

@staff_member_required
def actualizar_cupos_pago_manual(request):
    if request.method == 'POST':
        usuario_id = request.POST.get('usuario_id')
        nuevos_cupos = request.POST.get('nuevos_cupos')
        perfil = get_object_or_404(Perfil, usuario_id=usuario_id)
        perfil.clases_disponibles = nuevos_cupos
        perfil.save()
        messages.success(request, f"Cupos de {perfil.usuario.first_name} actualizados a {nuevos_cupos}.")
    return redirect('reporte_ganancias')

@staff_member_required
def sumar_cupo_rapido(request, usuario_id):
    if request.method == 'POST':
        perfil = get_object_or_404(Perfil, usuario_id=usuario_id)
        perfil.clases_disponibles += 1
        perfil.save()
        return JsonResponse({'status': 'ok'})

import random
from django.contrib.auth.models import User
from .models import Perfil, MovimientoCaja, Pago # Ajustá los imports a tus apps
from kiosco.models import Producto
from django.utils import timezone
from datetime import timedelta

@staff_member_required
def generar_data_masiva(request):
    cantidad = 500  # Probamos con 500 por cada click
    usuarios_a_crear = []
    
    for i in range(cantidad):
        id_unico = random.randint(10000, 999999)
        usuarios_a_crear.append(User(
            username=f"socio_{id_unico}",
            first_name=f"SocioTest",
            last_name=f"Numero_{id_unico}",
            email=f"test_{id_unico}@gym.com"
        ))
    
    # Creamos los usuarios masivamente
    User.objects.bulk_create(usuarios_a_crear)
    
    # IMPORTANTE: Como bulk_create no dispara "signals", 
    # tenemos que crear los Perfiles manualmente para esos nuevos usuarios
    usuarios_sin_perfil = User.objects.filter(perfil__isnull=True)
    perfiles_a_crear = [
        Perfil(usuario=u, clases_disponibles=random.randint(0, 12), telefono="12345678") 
        for u in usuarios_sin_perfil
    ]
    Perfil.objects.bulk_create(perfiles_a_crear)

    messages.success(request, f"🚀 Se cargaron {cantidad} usuarios en tiempo récord.")
    return redirect('recepcion')




@staff_member_required
def generar_data_test(request):
    # 1. CREAR PRODUCTOS (KIOSCO)
    nombres_prod = ["Proteína Gold", "Creatina 300g", "Barrita Proteica", "Agua 500ml", "Bebida Isotónica", "Remera Gym"]
    for nombre in nombres_prod:
        Producto.objects.get_or_create(
            nombre=nombre,
            defaults={'precio': random.randint(500, 5000), 'stock': random.randint(10, 100)}
        )

    # 2. CREAR USUARIOS MASIVOS (SOCIOS)
    # Vamos a crear 50 usuarios de prueba para no saturar de un solo golpe
    for i in range(50):
        username = f"socio_test_{random.randint(1000, 99999)}"
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(
                username=username,
                password="password123",
                first_name=f"Nombre_{i}",
                last_name=f"Apellido_{i}",
                email=f"{username}@test.com"
            )
            # El signal crea el Perfil, pero lo editamos
            perfil = user.perfil
            perfil.clases_disponibles = random.randint(-5, 20) # Algunos morosos, otros con crédito
            perfil.telefono = f"11{random.randint(11111111, 99999999)}"
            perfil.save()

    # 3. CREAR MOVIMIENTOS DE CAJA (Para el gráfico y caja diaria)
    metodos = ['EFECTIVO', 'TRANSFERENCIA', 'TARJETA']
    for _ in range(30):
        tipo = random.choice(['INGRESO', 'EGRESO'])
        MovimientoCaja.objects.create(
            tipo=tipo,
            monto=random.randint(1000, 15000),
            concepto="Movimiento de Prueba Automático",
            metodo=random.choice(metodos),
            fecha=timezone.now() - timedelta(days=random.randint(0, 30)) # Movimientos en el último mes
        )

    messages.success(request, "✅ Data de prueba generada: 50 Usuarios, Productos y 30 Movimientos.")
    return redirect('caja_diaria')

@staff_member_required
@user_passes_test(es_admin) # Solo el superusuario puede resetear la DB
def reset_base_datos(request):
    try:
        with transaction.atomic():
            # Borramos todos los usuarios que NO sean staff/superuarios
            usuarios_test = User.objects.filter(is_staff=False, is_superuser=False)
            cantidad_usuarios = usuarios_test.count()
            usuarios_test.delete()
            
            # Borramos movimientos de caja y productos
            MovimientoCaja.objects.all().delete()
            Producto.objects.all().delete()
            # Si tenés el modelo Pago, se borra en cascada al borrar el User, 
            # pero por las dudas:
            if 'Pago' in globals(): Pago.objects.all().delete()

        messages.success(request, f"💣 Sistema reseteado: Se eliminaron {cantidad_usuarios} usuarios y toda la data de prueba.")
    except Exception as e:
        messages.error(request, f"❌ Error al resetear: {str(e)}")
        
    return redirect('caja_diaria')