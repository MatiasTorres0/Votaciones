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
        
# Formulario para Media
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
# Formulario para Opción
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
    Formulario para manejar los votos con la gestión adecuada del nombre de usuario.
    """
    nombre_twitch = forms.CharField(
        label='Nombre de Twitch',
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese su nombre de Twitch',
                'pattern': '[A-Za-z0-9_]+',
                'maxlength': '25'
            }
        )
    )

    class Meta:
        model = Formulario
        fields = ['nombre_twitch', 'pregunta', 'opcion']
        widgets = {
            'pregunta': forms.HiddenInput(),
            'opcion': forms.RadioSelect(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        pregunta_id = kwargs.pop('pregunta_id', None)
        super().__init__(*args, **kwargs)
        
        if pregunta_id:
            try:
                pregunta_object = Pregunta.objects.get(pk=pregunta_id)
                self.fields['pregunta'].initial = pregunta_id
                self.fields['opcion'].queryset = pregunta_object.opciones.all()
            except Pregunta.DoesNotExist:
                raise forms.ValidationError("Pregunta no encontrada")

    def clean(self):
        """
        Valida los datos del formulario y asegura que el nombre de usuario se gestione correctamente.
        """
        cleaned_data = super().clean()
        nombre_twitch = cleaned_data.get('nombre_twitch', '').strip()
        pregunta = cleaned_data.get('pregunta')
        opcion = cleaned_data.get('opcion')

        logger.debug(f"Form Clean: nombre_twitch={nombre_twitch}, pregunta={pregunta}, opcion={opcion}")

        # Requiere el nombre de usuario condicionalmente basado en la sesión
        if not self.initial.get('nombre_twitch') and not nombre_twitch:
            raise forms.ValidationError("El nombre de Twitch es requerido para votar por primera vez.")

        if nombre_twitch and pregunta and opcion:
            # Verifica si ya existe un voto con este nombre de usuario para esta pregunta y opción específicas
            existing_vote = Formulario.objects.filter(
                pregunta=pregunta,
                usuario=nombre_twitch,
                opcion=opcion
            ).exists()

            if existing_vote:
                logger.debug(f"Form Clean: Usuario {nombre_twitch} ya ha votado para esta pregunta con esta opción")
                raise ValidationError(
                        "Ya has votado en esta pregunta con esta opción."
                    )
            
            logger.debug(f"Form Clean: Usuario {nombre_twitch} no ha votado antes para esta pregunta con esta opción")
            cleaned_data['nombre_twitch'] = nombre_twitch
        
        return cleaned_data

    def save(self, commit=True):
        """
        Anula el método save para asegurar que el nombre de usuario se guarde correctamente.
        """
        instance = super().save(commit=False)
        
        # Asegura que ambos campos de nombre de usuario estén establecidos
        twitch_name = self.cleaned_data.get('nombre_twitch')
        
        # Utiliza el nombre de usuario inicial si no se proporcionó un nuevo nombre de usuario
        if not twitch_name:
            twitch_name = self.initial.get('nombre_twitch')

        instance.usuario = twitch_name
        instance.nombre_twitch = twitch_name

        logger.debug(f"Form Save: Usuario {twitch_name} está guardando un voto")
        
        if commit:
            instance.save()
        
        return instance
