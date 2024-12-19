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
    nombre_twitch = forms.CharField(label='Nombre de Twitch', widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su Nombre de Twitch'}))
    class Meta:
        model = Formulario
        fields = ['nombre_twitch', 'pregunta', 'opcion']
        widgets = {
            'pregunta': forms.HiddenInput(),
            'opcion': forms.RadioSelect()
        }
    
    def __init__(self, *args, **kwargs):
          pregunta_id = kwargs.pop('pregunta_id', None) #getting the question id
          super().__init__(*args, **kwargs)
          if pregunta_id:
              self.fields['pregunta'].initial = pregunta_id # setting the initial value based on the url
              pregunta_object = Pregunta.objects.get(pk=pregunta_id)  # Get the Pregunta object
              self.fields['opcion'].queryset = pregunta_object.opciones.all()