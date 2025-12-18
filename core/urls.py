from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from rest_framework import routers
from django.urls.conf import include

router = routers.DefaultRouter()
router.register('pregunta', views.PreguntaViewSet)
router.register('opcion', views.OpcionViewSet)



urlpatterns = [
    path('mantenimiento', views.mantenimiento, name="mantenimiento"),
    path('', views.inicio, name='inicio'), # Pagina de Inicio
    path('crear_encuesta/', views.crear_encuesta, name='crear_encuesta'),  # Form para crear una encuesta
    path('lista_encuestas/', views.lista_encuestas, name='lista_encuestas'), # Muestra la lista de encuestas
    path('editar_encuesta/<int:encuesta_id>/', views.editar_encuesta, name='editar_encuesta'), # Muestra la lista de encuestas
    path('crear_pregunta/<int:encuesta_id>/', views.crear_pregunta, name='crear_pregunta'),  # Form para crear preguntas
    path('crear_opcion/<int:pregunta_id>/', views.crear_opcion, name='crear_opcion'), # Form para crear opciones
    path('votaciones/<int:pregunta_id>/<int:opcion_id>/', views.votaciones, name='votaciones'),  # Form para las votaciones
    path('resultados/<int:encuesta_id>/', views.resultados, name='resultados'), # Resultados
    path('editar_pregunta/<int:pregunta_id>/', views.editar_pregunta, name='editar_pregunta'), # Muestra la lista de encuestas
    path('lista_preguntas/<int:encuesta_id>/', views.lista_preguntas, name='lista_preguntas'),
    path('crear_media/<int:pregunta_id>/', views.crear_media, name='crear_media'),
    path('lista_opciones/<int:pregunta_id>/', views.lista_opciones, name='lista_opciones'),
    path('editar_opcion/<int:opcion_id>/', views.editar_opcion, name='editar_opcion'),
    path('home', views.home, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('eliminar_encuesta/<int:encuesta_id>/', views.eliminar_encuesta, name='eliminar_encuesta'),
    path('eliminar_pregunta/<int:pregunta_id>/', views.eliminar_pregunta, name='eliminar_pregunta'),
    path('eliminar_opcion/<int:opcion_id>/', views.eliminar_opcion, name='eliminar_opcion'),
    path('lista_medias/<int:pregunta_id>/', views.lista_medias, name='lista_medias'),
    path('eliminar_media/<int:media_id>/', views.eliminar_media, name='eliminar_media'),
    path('error_404/', views.error_404, name='error_404'),
    path('api/', include(router.urls)),
    path('descargar_resultados/<int:encuesta_id>/', views.descargar_resultados, name='descargar_resultados'),
    path('comparar_resultados/', views.comparar_resultados, name='comparar_resultados'),
]
# Sirve archivos de media en modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)