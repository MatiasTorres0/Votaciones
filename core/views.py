from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from .forms import EncuestaForm, PreguntaForm, OpcionForm, FormularioForm, MediaForm
from .models import Encuesta, Pregunta, Opcion, Formulario, Media
from django.contrib import messages  # Import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout

#rest_framework
from rest_framework import viewsets
from .serializers import PreguntaSerializer, OpcionSerializer

def inicio(request):
    """
    Displays the voting interface and handles the initial username submission.
    """
    # Handle initial form submission and set session
    if request.method == 'POST':
        nombre_twitch = request.POST.get('nombre_twitch')
        
        if not nombre_twitch:
            messages.error(request, "El nombre de Twitch es requerido")
            return render(request, 'core/inicio.html')
        
        # Store username in session
        request.session['twitch_name'] = nombre_twitch
        return redirect('inicio')

    # Get user information from the session
    twitch_name = request.session.get('twitch_name')
    preguntas = Pregunta.objects.all()
    
    # Prepare preguntas
    preguntas_con_voto = []
    for pregunta in preguntas:
        ha_votado = pregunta.formulario_set.filter(usuario=twitch_name).exists() if twitch_name else False
        preguntas_con_voto.append({
            'pregunta': pregunta,
            'ha_votado': ha_votado
        })

    # Render the page
    return render(
        request,
        'core/inicio.html',
        {
            'preguntas': preguntas_con_voto,
            'twitch_name': twitch_name
        }
    )
@login_required
def crear_encuesta(request):
    if request.method == 'POST':
        form = EncuestaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_encuestas')
    else:
        form = EncuestaForm()
    return render(request, 'core/crear_encuesta.html', {'form': form})
@login_required
def lista_encuestas(request):
    encuestas = Encuesta.objects.all()
    return render(request, 'core/lista_encuestas.html', {'encuestas': encuestas})
@login_required
def editar_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    if request.method == 'POST':
        form = EncuestaForm(request.POST, instance=encuesta)
        if form.is_valid():
            form.save()
            return redirect('lista_encuestas')
    else:
        form = EncuestaForm(instance=encuesta)
    return render(request, 'core/editar_encuesta.html', {'form': form, 'encuesta': encuesta})
@login_required
def crear_pregunta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    if request.method == 'POST':
        form = PreguntaForm(request.POST)
        if form.is_valid():
            pregunta = form.save(commit=False)
            pregunta.encuesta = encuesta
            pregunta.save()
            return redirect('editar_encuesta', encuesta_id=encuesta.id)
    else:
        form = PreguntaForm()
    return render(request, 'core/crear_pregunta.html', {'form': form, 'encuesta': encuesta})
@login_required
def editar_pregunta(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    if request.method == 'POST':
        form = PreguntaForm(request.POST, instance=pregunta)
        if form.is_valid():
            form.save()
            return redirect('editar_encuesta', encuesta_id=pregunta.encuesta.id)
    else:
        form = PreguntaForm(instance=pregunta)
    return render(request, 'core/editar_pregunta.html', {'form': form, 'pregunta': pregunta})
@login_required
def crear_pregunta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    if request.method == 'POST':
        form = PreguntaForm(request.POST)
        if form.is_valid():
            pregunta = form.save(commit=False)
            pregunta.encuesta = encuesta
            pregunta.save()
            return redirect('lista_preguntas', encuesta_id=encuesta.id)
    else:
        form = PreguntaForm()
    return render(request, 'core/crear_pregunta.html', {'form': form, 'encuesta': encuesta})
@login_required
def crear_media(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    if request.method == 'POST':
        form = MediaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('lista_preguntas', encuesta_id=pregunta.encuesta.id)
    else:
        form = MediaForm()
    return render(request, 'core/crear_media.html', {'form': form, 'pregunta': pregunta})
@login_required
def crear_opcion(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    if request.method == 'POST':
        form = OpcionForm(request.POST)
        if form.is_valid():
            opcion = form.save(commit=False)
            opcion.pregunta = pregunta
            opcion.save()
            form.save_m2m()
            return redirect('lista_opciones', pregunta_id=pregunta.id)
    else:
        form = OpcionForm()
    return render(request, 'core/crear_opcion.html', {'form': form, 'pregunta': pregunta})

def votaciones(request, pregunta_id, opcion_id):
    """
    Handles the voting process with proper user session management.
    
    Args:
        request: HttpRequest object
        pregunta_id: ID of the question being voted on
        opcion_id: ID of the selected option
    """
    # Get required objects
    pregunta = get_object_or_404(Pregunta, pk=pregunta_id)
    opcion = get_object_or_404(Opcion, pk=opcion_id)
    
    # First-time user handling
    if 'twitch_name' not in request.session:
        if request.method == 'POST':
            # Process initial username submission
            form = FormularioForm(request.POST, pregunta_id=pregunta_id)
            if form.is_valid():
                 try:
                    # Get username from form
                    twitch_name = form.cleaned_data['nombre_twitch']
                    
                    # Create and save the vote
                    voto = form.save(commit=False)
                    voto.usuario = twitch_name
                    voto.nombre_twitch = twitch_name  # Set both fields
                    voto.save()
                    
                    # Store in session after successful vote
                    request.session['twitch_name'] = twitch_name
                    messages.success(request, "¡Gracias por tu voto!")
                    return redirect('inicio')
                 except ValidationError as e:
                    messages.error(request, f"Error al votar: {str(e)}")
                    return redirect('inicio')
            else:
                #Form Invalid
                messages.error(request, "Error al votar. Por favor, verifica el formulario.")
        else:
            # Initial form display
            form = FormularioForm(
                initial={'pregunta': pregunta_id, 'opcion': opcion_id},
                pregunta_id=pregunta_id
            )
            
        return render(
            request,
            'core/votacion.html',
            {
                'form': form,
                'mensaje': '¡Bienvenido a las votaciones, para comenzar agrega tú nombre de twitch!',
                'pregunta': pregunta,
                'first_time': True,
                'opcion': opcion
            }
        )
    
    # Returning user handling
    if request.method == 'POST':
        form = FormularioForm(request.POST, initial={'nombre_twitch': request.session.get('twitch_name')}, pregunta_id=pregunta_id)
        if form.is_valid():
            try:
                # Use session username for the vote
                twitch_name = request.session['twitch_name']
                
                # Create and save the vote with session username
                voto = form.save(commit=False)
                voto.usuario = twitch_name
                voto.nombre_twitch = twitch_name  # Set both fields
                voto.save()
                
                messages.success(request, "¡Gracias por tu voto!")
                return redirect('inicio')
                
            except ValidationError as e:
                messages.error(request, f"Error al votar: {str(e)}")
                return redirect('inicio')
        else:
            #Form Invalid
             messages.error(request, "Error al votar. Por favor, verifica el formulario.")
    else:
        # Display form for returning user
        form = FormularioForm(
            initial={
                'pregunta': pregunta_id,
                'opcion': opcion_id,
                'nombre_twitch': request.session.get('twitch_name')  # Pre-fill username
            },
            pregunta_id=pregunta_id
        )
    
    return render(
        request,
        'core/votacion.html',
        {
            'form': form,
            'mensaje': '¡Ya puedes votar!',
            'pregunta': pregunta,
            'first_time': False,
            'opcion': opcion
        }
    )
@login_required
def resultados(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    preguntas = encuesta.preguntas.all()
    resultados_por_pregunta = []

    for pregunta in preguntas:
        resultados_opciones = []
        opciones = pregunta.opciones.all()
        total_votos = Formulario.objects.filter(pregunta=pregunta).count()

        for opcion in opciones:
            votos_opcion = Formulario.objects.filter(pregunta=pregunta, opcion=opcion).count()
            porcentaje = (votos_opcion / total_votos * 100) if total_votos > 0 else 0
            resultados_opciones.append({
                'opcion': opcion,
                'votos': votos_opcion,
                'porcentaje': round(porcentaje, 2)
            })

        resultados_por_pregunta.append({'pregunta': pregunta, 'resultados': resultados_opciones})

    return render(request, 'core/resultados.html', {'encuesta': encuesta, 'resultados_por_pregunta': resultados_por_pregunta})
@login_required
def lista_preguntas(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    preguntas = Pregunta.objects.filter(encuesta=encuesta)
    return render(request, 'core/lista_preguntas.html', {'encuesta': encuesta, 'preguntas': preguntas})
@login_required
def lista_opciones(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    opciones = Opcion.objects.filter(pregunta=pregunta)
    return render(request, 'core/lista_opciones.html', {'pregunta': pregunta, 'opciones': opciones})
@login_required
def editar_opcion(request, opcion_id):
    opcion = get_object_or_404(Opcion, id=opcion_id)
    if request.method == 'POST':
        form = OpcionForm(request.POST, instance=opcion)
        if form.is_valid():
            form.save()
            return redirect('lista_opciones', pregunta_id=opcion.pregunta.id)
    else:
        form = OpcionForm(instance=opcion)
    return render(request, 'core/editar_opcion.html', {'form': form, 'opcion': opcion})

def mantenimiento(request):
    return render(request, 'core/mantenimiento.html')

def home(request):
    return  render(request, 'core/home.html')

def logout_view(request):
    print("Proceso de cierre de sesión iniciado")
    logout(request)
    print("Función logout llamada, sesión limpiada")
    return redirect('inicio')  # Redirige a la página de inicio


def error_404(request, exception):
    return render(request, 'core/404.html', status=404)
@login_required
def eliminar_opcion(request, opcion_id):
    opcion = get_object_or_404(Opcion, id=opcion_id)
    pregunta_id = opcion.pregunta.id
    opcion.delete()
    return redirect('lista_opciones', pregunta_id=pregunta_id)
@login_required
def eliminar_pregunta(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    encuesta_id = pregunta.encuesta.id
    pregunta.delete()
    return redirect('lista_preguntas', encuesta_id=encuesta_id)
@login_required
def eliminar_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    encuesta.delete()
    return redirect('lista_encuestas')
@login_required
def lista_medias(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    medias = Media.objects.filter(pregunta=pregunta)
    return render(request, 'core/lista_medias.html', {'pregunta': pregunta, 'medias': medias})



class PreguntaViewSet(viewsets.ModelViewSet):
    queryset = Pregunta.objects.all()
    serializer_class = PreguntaSerializer

class OpcionViewSet(viewsets.ModelViewSet):
    queryset = Opcion.objects.all()
    serializer_class = OpcionSerializer