from django import forms
from .models import Encuesta, Pregunta, Opcion, Formulario, Media
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)



# Formulario para Encuesta
class EncuestaForm(forms.ModelForm):
    class Meta:
        model = Encuesta
        fields = ['titulo', 'descripcion', 'streamer', 'estado']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título de la encuesta'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descripción opcional'}),
            'streamer': forms.Select(attrs={'class': 'form-control'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'titulo': 'Título',
            'descripcion': 'Descripción',
            'streamer': 'Streamer',
        }

class PreguntaForm(forms.ModelForm):
    class Meta:
        model = Pregunta
        fields = ['pregunta', 'streamer']
        widgets = {
            'pregunta': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Escribe la pregunta aquí',
                'rows': 3
            }),
            # AQUÍ ESTÁ EL CAMBIO IMPORTANTE:
            'streamer': forms.Select(attrs={
                'class': 'form-select'  # Usar form-select en lugar de form-control
            }),
        }
        labels = {
            'pregunta': 'Pregunta',
            'streamer': 'Streamer',
        }
        
# Formulario para Media
class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['tipo_media', 'archivo', 'url_youtube', 'streamer']
        widgets = {
            'tipo_media': forms.RadioSelect(),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'url_youtube': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/...'}),
            'streamer': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'tipo_media': 'Tipo de Media',
            'archivo': 'Subir Archivo',
            'url_youtube': 'URL de YouTube',
            'streamer': 'Streamer',
        }

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
        fields = ['opcion', 'medias', 'color', 'streamer']
        widgets = {
            'opcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opción de respuesta'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'streamer': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'opcion': 'Opción',
            'color': 'Color de la Opción',
            'streamer': 'Streamer',
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
        fields = ['nombre_twitch', 'pregunta', 'opcion', 'streamer']
        widgets = {
            'pregunta': forms.HiddenInput(),
            'opcion': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'streamer': forms.HiddenInput(),
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