from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
import os

from .models import Encuesta, Pregunta, Opcion, Formulario, Media

import logging
import re

logger = logging.getLogger(__name__)


class EncuestaForm(forms.ModelForm):
    class Meta:
        model = Encuesta
        fields = ['titulo', 'descripcion', 'fecha_inicio', 'fecha_fin']
        widgets = {
            'titulo': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ej: Satisfacción del cliente 2024',
                }
            ),
            'descripcion': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Describe el propósito de la encuesta (opcional)',
                }
            ),
            'fecha_inicio': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'fecha_fin': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name in ['fecha_inicio', 'fecha_fin']:
            value = self.initial.get(field_name)

            if not value and getattr(self.instance, 'pk', None):
                value = getattr(self.instance, field_name, None)

            if value:
                local_value = timezone.localtime(value) if timezone.is_aware(value) else value
                self.initial[field_name] = local_value.strftime('%Y-%m-%dT%H:%M')


class PreguntaForm(forms.ModelForm):
    class Meta:
        model = Pregunta
        fields = ['pregunta']
        widgets = {
            'pregunta': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Escribe la pregunta aquí',
                'rows': 3
            }),
        }
        labels = {
            'pregunta': 'Pregunta',
        }


class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['nombre', 'tipo_media', 'archivo', 'url_youtube']
        widgets = {
            'tipo_media': forms.RadioSelect(),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre descriptivo (opcional)'
            }),
            'url_youtube': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.youtube.com/watch?v=... o https://youtu.be/...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['archivo'].required = False
        self.fields['url_youtube'].required = False
        self.fields['nombre'].required = False
    
    def extract_youtube_id(self, url):
        """Extrae el ID de video de una URL de YouTube"""
        if not url:
            return None
        
        # Patrones para diferentes formatos de URL de YouTube
        patterns = [
            r'youtu\.be/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                # Verificar que sea un ID válido (11 caracteres)
                if len(video_id) == 11:
                    return video_id
        
        return None
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_media = cleaned_data.get('tipo_media')
        archivo = cleaned_data.get('archivo')
        url_youtube = cleaned_data.get('url_youtube')
        
        if tipo_media == 'LOCAL':
            if not archivo:
                raise forms.ValidationError("Debes seleccionar un archivo para 'Archivo Local'")
            
            # Validar tipo de archivo
            if archivo:
                valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mov', '.webm', '.mkv']
                file_extension = os.path.splitext(archivo.name)[1].lower()
                
                if file_extension not in valid_extensions:
                    raise forms.ValidationError(
                        f"Formato de archivo no válido. Formatos aceptados: {', '.join(valid_extensions)}"
                    )
                
                # Validar tamaño máximo (ej: 100MB)
                max_size = 100 * 1024 * 1024  # 100MB
                if archivo.size > max_size:
                    raise forms.ValidationError(
                        f"El archivo es demasiado grande. Tamaño máximo: {max_size/(1024*1024)}MB"
                    )
            
            if url_youtube:
                self.add_error('url_youtube', "No ingreses URL cuando subes un archivo local")
        
        elif tipo_media == 'YOUTUBE':
            if not url_youtube:
                raise forms.ValidationError("Debes ingresar una URL de YouTube")
            
            # Validar formato básico de URL
            if not url_youtube.startswith(('http://', 'https://')):
                raise forms.ValidationError("La URL debe comenzar con http:// o https://")
            
            # Validar que sea dominio de YouTube
            if 'youtube.com' not in url_youtube and 'youtu.be' not in url_youtube:
                raise forms.ValidationError("Debe ser una URL de YouTube (youtube.com o youtu.be)")
            
            # Extraer ID de video para validación adicional
            video_id = self.extract_youtube_id(url_youtube)
            if not video_id:
                raise forms.ValidationError(
                    "URL de YouTube no válida. Formatos aceptados:\n"
                    "- https://www.youtube.com/watch?v=ID\n"
                    "- https://youtu.be/ID\n"
                    "- https://www.youtube.com/shorts/ID\n"
                    "- https://www.youtube.com/embed/ID"
                )
            
            if archivo:
                self.add_error('archivo', "No subas archivo cuando ingresas una URL de YouTube")
        
        return cleaned_data


class OpcionForm(forms.ModelForm):
    medias = forms.ModelMultipleChoiceField(
        queryset=Media.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Medios Asociados"
    )

    class Meta:
        model = Opcion
        fields = ['opcion', 'medias', 'color']
        widgets = {
            'opcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opción de respuesta'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }
        labels = {
            'opcion': 'Opción',
            'color': 'Color de la Opción',
        }


class FormularioForm(forms.ModelForm):
    """
    Formulario para manejar los votos.
    El nombre de Twitch se obtiene automáticamente de la sesión.
    """
    
    class Meta:
        model = Formulario
        fields = ['pregunta', 'opcion']
        widgets = {
            'pregunta': forms.HiddenInput(),
            'opcion': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, pregunta_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar opciones según la pregunta
        if pregunta_id:
            try:
                pregunta_object = Pregunta.objects.get(pk=pregunta_id)
                self.fields['pregunta'].initial = pregunta_id
                self.fields['opcion'].queryset = pregunta_object.opciones.all()
            except Pregunta.DoesNotExist:
                raise forms.ValidationError("Pregunta no encontrada")
        
        # Label personalizado
        self.fields['opcion'].label = 'Selecciona tu opción'

    def clean(self):
        """
        Validación del formulario.
        """
        cleaned_data = super().clean()
        pregunta = cleaned_data.get('pregunta')
        opcion = cleaned_data.get('opcion')

        logger.debug(f"Form Clean: pregunta={pregunta}, opcion={opcion}")

        # Validar que la opción pertenece a la pregunta
        if pregunta and opcion:
            if opcion.pregunta != pregunta:
                raise forms.ValidationError("La opción seleccionada no pertenece a esta pregunta.")
        
        return cleaned_data