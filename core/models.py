from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, RegexValidator

class Encuesta(models.Model):
    titulo = models.CharField(max_length=200)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.titulo

class Pregunta(models.Model):
    encuesta = models.ForeignKey(Encuesta, on_delete=models.CASCADE, related_name='preguntas', null=True)
    pregunta = models.TextField(null=True)

    def __str__(self):
        return self.pregunta

class Media(models.Model):
    TIPO_MEDIA = (
        ('LOCAL', 'Archivo Local'),
        ('YOUTUBE', 'YouTube'),
    )

    tipo_media = models.CharField(max_length=10, choices=TIPO_MEDIA, default='LOCAL')
    archivo = models.FileField(upload_to='media/', blank=True, null=True)
    url_youtube = models.URLField(blank=True, null=True)

    def clean(self):
        super().clean()
        if self.tipo_media == 'LOCAL' and not self.archivo:
            raise ValidationError("Se debe subir un archivo local para esta opción.")
        elif self.tipo_media == 'YOUTUBE' and not self.url_youtube:
            raise ValidationError("Se debe ingresar una URL de YouTube para esta opción.")

    def get_youtube_embed_url(self):
        if self.tipo_media == 'YOUTUBE' and self.url_youtube:
            url = self.url_youtube
            if "youtu.be" in url:
                video_id = url.split("youtu.be/")[1]
            else:
                video_id = url.split("v=")[1].split("&")[0]
            return f'https://www.youtube.com/embed/{video_id}'
        return None

    def __str__(self):
        return self.archivo.name if self.tipo_media == 'LOCAL' else self.url_youtube

class Opcion(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones', null=True)
    opcion = models.CharField(max_length=200)
    medias = models.ManyToManyField(Media, related_name='opciones', blank=True)
    color = models.CharField(max_length=7, blank=True, default="#28a745", validators=[
        RegexValidator(r'^#[0-9A-Fa-f]{6}$', message="El color debe ser un código hexadecimal válido.")
    ])

    def __str__(self):
        return self.opcion

class Formulario(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, null=True)
    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE, null=True)
    nombre_twitch = models.CharField(max_length=200, blank=True)
    color = models.CharField(max_length=7, blank=True, default="#ffffff", validators=[
        RegexValidator(r'^#[0-9A-Fa-f]{6}$', message="El color debe ser un código hexadecimal válido.")
    ])

    def __str__(self):
        return f'Voto en {self.pregunta} por {self.opcion}'
