from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
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
]
# Sirve archivos de media en modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)