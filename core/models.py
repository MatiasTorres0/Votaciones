import re
import logging
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model

# Configuración del logger
logger = logging.getLogger(__name__)

User = get_user_model()

class Encuesta(models.Model):
    ESTADO = (
        ('ACTIVA', 'Activa'),
        ('TERMINADA', 'Terminada'),
        ('PROGRAMADA', 'Programada'), # Nuevo estado para encuestas futuras
    )
    estado = models.CharField(max_length=10, choices=ESTADO, default='ACTIVA')
    titulo = models.CharField(max_length=200)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    # Temporizadores para activación automática
    fecha_inicio = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora para activar la encuesta automáticamente.")
    fecha_fin = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora para terminar la encuesta automáticamente.")
    
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.titulo

    def get_color(self):
        """Obtiene el color asociado a la encuesta basado en el primer voto."""
        if self.preguntas.exists():
            for pregunta in self.preguntas.all():
               if pregunta.formulario_set.exists():
                  return pregunta.formulario_set.first().color
        return "#ffffff"

    def clean(self):
        """
        Validaciones robustas para la encuesta.
        - Valida coherencia de fechas (inicio < fin).
        """
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio >= self.fecha_fin:
            raise ValidationError("La fecha de inicio debe ser anterior a la fecha de fin.")

    def save(self, *args, **kwargs):
        """
        Sobrescribe save para implementar lógica de activación automática y logging.
        """
        # Lógica de activación automática basada en fechas
        now = timezone.now()
        
        if self.fecha_inicio:
            if now < self.fecha_inicio:
                self.estado = 'PROGRAMADA'
            elif self.fecha_fin and now >= self.fecha_fin:
                self.estado = 'TERMINADA'
            elif now >= self.fecha_inicio:
                # Si ya pasó la fecha de inicio y no ha terminado
                if self.estado == 'PROGRAMADA':
                     self.estado = 'ACTIVA'
                     logger.info(f"Encuesta '{self.titulo}' activada automáticamente por temporizador.")
        
        # Log del guardado
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        action = "creada" if is_new else "actualizada"
        logger.info(f"Encuesta '{self.titulo}' (ID: {self.pk}) {action}. Estado: {self.estado}")

class Pregunta(models.Model):
    encuesta = models.ForeignKey(Encuesta, on_delete=models.CASCADE, related_name='preguntas', null=True)
    pregunta = models.TextField(null=True)

    def __str__(self):
        return self.pregunta

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            logger.debug(f"Nueva pregunta creada: '{self.pregunta}' en encuesta ID {self.encuesta_id}")

class Media(models.Model):
    TIPO_MEDIA = (
        ('LOCAL', 'Archivo Local'),
        ('YOUTUBE', 'YouTube'),
    )

    nombre = models.CharField(max_length=200, blank=True, null=True)
    tipo_media = models.CharField(max_length=10, choices=TIPO_MEDIA, default='LOCAL')
    archivo = models.FileField(upload_to='media/', blank=True, null=True)
    url_youtube = models.URLField(blank=True, null=True)
    pregunta = models.ForeignKey('Pregunta', on_delete=models.CASCADE, related_name='medias', null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.tipo_media == 'LOCAL' and not self.archivo:
            raise ValidationError("Se debe subir un archivo local para esta opción.")
        elif self.tipo_media == 'YOUTUBE' and not self.url_youtube:
            raise ValidationError("Se debe ingresar una URL de YouTube para esta opción.")

    def get_youtube_embed_url(self):
        """Obtiene la URL de embed de YouTube de forma segura con prevención de error 153"""
        if self.tipo_media != 'YOUTUBE' or not self.url_youtube:
            return None
        
        try:
            url = self.url_youtube.strip()
            logger.info(f"Procesando URL de YouTube: {url}")
            
            # Patrones para diferentes formatos de URL de YouTube
            patterns = [
                # youtu.be/ID
                r'youtu\.be/([a-zA-Z0-9_-]{11})',
                # youtube.com/watch?v=ID
                r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
                # youtube.com/shorts/ID
                r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
                # youtube.com/embed/ID
                r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
                # youtube.com/v/ID
                r'youtube\.com/v/([a-zA-Z0-9_-]{11})',
                # youtube.com/watch?v=ID&otros_parametros
                r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
                # youtube-nocookie.com/embed/ID (ya procesado)
                r'youtube-nocookie\.com/embed/([a-zA-Z0-9_-]{11})'
            ]
            
            video_id = None
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    video_id = match.group(1)
                    logger.info(f"ID de video encontrado: {video_id}")
                    break
            
            if video_id and len(video_id) == 11:  # Los IDs de YouTube tienen 11 caracteres
                # Usar youtube-nocookie.com para mejor privacidad y prevenir error 153
                embed_url = f'https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1'
                logger.info(f"URL de embed generada: {embed_url}")
                return embed_url
            else:
                logger.warning(f"No se pudo extraer ID válido de la URL: {url}")
        
        except Exception as e:
            logger.error(f"Error al procesar URL de YouTube: {e}")
            logger.error(f"URL problemática: {self.url_youtube}")
        
        return None

    def __str__(self):
        if self.nombre:
            return self.nombre
        elif self.tipo_media == 'LOCAL' and self.archivo:
            return self.archivo.name
        elif self.tipo_media == 'YOUTUBE' and self.url_youtube:
            return self.url_youtube
        return f"Media {self.id}"
   
class Opcion(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones', null=True)
    opcion = models.CharField(max_length=200)
    medias = models.ManyToManyField(Media, related_name='opciones_media', blank=True)
    color = models.CharField(max_length=7, blank=True, default="#28a745", validators=[
        RegexValidator(r'^#[0-9A-Fa-f]{6}$', message="El color debe ser un código hexadecimal válido.")
    ])
    
    def __str__(self):
        return self.opcion

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
             logger.debug(f"Opción '{self.opcion}' agregada a pregunta ID {self.pregunta_id}")


class Formulario(models.Model):
    nombre_twitch = models.CharField(max_length=100, null=True)
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, null=True)
    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE, null=True)
    fecha_votacion = models.DateTimeField(auto_now_add=True, null=True)
    usuario = models.CharField(max_length=100, blank=True, null=True)

    def clean(self):
      if self.pregunta and self.opcion and self.usuario:
          if Formulario.objects.filter(pregunta=self.pregunta, usuario=self.usuario).exists():
            raise ValidationError('Ya has votado en esta pregunta.')

    def save(self, *args, **kwargs):
         self.usuario=self.nombre_twitch #Setting the user as the name provided at creation
         super().save(*args, **kwargs)
         logger.info(f"Voto registrado: Usuario '{self.usuario}' en Pregunta ID {self.pregunta_id}")

    def __str__(self):
       return f"Voto de {self.usuario} en {self.pregunta}"