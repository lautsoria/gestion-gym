from django.urls import path
from . import views

urlpatterns = [
    # Página principal: Horarios
    path('', views.ver_horarios, name='horarios'), 
    
    # Perfil y Reservas del Socio
    path('registro/', views.RegistroUsuario.as_view(), name='signup'),
    path('mis-clases/', views.mis_clases, name='mis_clases'),
    path('anotarse/<int:clase_id>/', views.inscribir_clase, name='anotarse'),
    path('cancelar/<int:inscripcion_id>/', views.cancelar_reserva, name='cancelar'),
    
    # Gestión y Administración (Staff)
    path('reporte/', views.reporte_ganancias, name='reporte_ganancias'),
    path('admin-clases/', views.lista_clases_admin, name='admin_clases'),
    path('asistencia/<int:clase_id>/', views.detalle_asistencia, name='asistencia'),
    path('marcar-asistencia/<int:inscripcion_id>/', views.marcar_asistencia, name='marcar_asistencia'),
    path('crear-admin-super-secreto-99/', views.crear_admin_magico),
]