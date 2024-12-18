from django import forms
from .models import Encuesta, Pregunta, Opcion, Formulario, Media

# Formulario para Encuesta
class EncuestaForm(forms.ModelForm):
    class Meta:
        model = Encuesta
        fields = ['titulo', 'descripcion']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título de la encuesta'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descripción opcional'}),
        }
        labels = {
            'titulo': 'Título',
            'descripcion': 'Descripción',
        }

# Formulario para Pregunta
class PreguntaForm(forms.ModelForm):
    class Meta:
        model = Pregunta
        fields = ['pregunta']
        widgets = {
            'pregunta': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Escribe la pregunta aquí'}),
        }
        labels = {
            'pregunta': 'Pregunta',
        }

# Formulario para Media
class MediaForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['tipo_media', 'archivo', 'url_youtube']
        widgets = {
            'tipo_media': forms.RadioSelect(),
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'url_youtube': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/...'}),
        }
        labels = {
            'tipo_media': 'Tipo de Media',
            'archivo': 'Subir Archivo',
            'url_youtube': 'URL de YouTube',
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
        fields = ['opcion', 'medias', 'color']
        widgets = {
            'opcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opción de respuesta'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }
        labels = {
            'opcion': 'Opción',
            'color': 'Color de la Opción',
        }

# Formulario para Registrar Voto
class FormularioForm(forms.ModelForm):
    class Meta:
        model = Formulario
        fields = ['pregunta', 'opcion', 'nombre_twitch', 'color']
        widgets = {
            'nombre_twitch': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre de Twitch'}),
            'pregunta': forms.HiddenInput(),
            'opcion': forms.HiddenInput(),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }
        labels = {
            'pregunta': 'Pregunta',
            'opcion': 'Opción',
            'nombre_twitch': 'Tu nombre de Twitch',
            'color': 'Color del formulario',
        }
