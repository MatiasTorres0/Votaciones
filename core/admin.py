from django.contrib import admin
from .models import Media, Opcion, Pregunta, Encuesta, Formulario, streamer
# Register your models here.
admin.site.register(Pregunta)
admin.site.register(Media)
admin.site.register(Opcion)
admin.site.register(Encuesta)
admin.site.register(Formulario)
admin.site.register(streamer)