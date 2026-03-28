from django.urls import path
from . import views

urlpatterns = [
    path('horarios/', views.ver_horarios, name='horarios_gym'),
    path('reporte/', views.reporte_ganancias, name='reporte_ganancias'),
    # Nueva URL que recibe un número entero (int) llamado clase_id
    path('anotarse/<int:clase_id>/', views.inscribir_clase, name='anotarse'),
    path('registro/', views.RegistroUsuario.as_view(), name='signup'),
    path('mis-clases/', views.mis_clases, name='mis_clases'),
    path('cancelar/<int:inscripcion_id>/', views.cancelar_reserva, name='cancelar'),
    path('admin-clases/', views.lista_clases_admin, name='admin_clases'),
    path('asistencia/<int:clase_id>/', views.detalle_asistencia, name='asistencia'),
]
