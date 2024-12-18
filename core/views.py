from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from .forms import EncuestaForm, PreguntaForm, OpcionForm, FormularioForm, MediaForm
from .models import Encuesta, Pregunta, Opcion, Formulario, Media


def inicio(request):
    preguntas = Pregunta.objects.all()
    return render(request, 'core/inicio.html', {'preguntas': preguntas})


def crear_encuesta(request):
    if request.method == 'POST':
        form = EncuestaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_encuestas')
    else:
        form = EncuestaForm()
    return render(request, 'core/crear_encuesta.html', {'form': form})


def lista_encuestas(request):
    encuestas = Encuesta.objects.all()
    return render(request, 'core/lista_encuestas.html', {'encuestas': encuestas})


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


def crear_pregunta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    if request.method == 'POST':
        form = PreguntaForm(request.POST)
        if form.is_valid():
            pregunta = form.save(commit=False)
            pregunta.encuesta = encuesta
            pregunta.save()
            return redirect('lista_preguntas', encuesta_id=encuesta.id) # Redirige a la lista de preguntas
    else:
        form = PreguntaForm()
    return render(request, 'core/crear_pregunta.html', {'form': form, 'encuesta': encuesta})
def crear_media(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    if request.method == 'POST':
        form = MediaForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('lista_preguntas', encuesta_id=pregunta.encuesta.id) # Redirige a la lista de preguntas
    else:
        form = MediaForm()
    return render(request, 'core/crear_media.html', {'form': form, 'pregunta': pregunta})
def crear_opcion(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    if request.method == 'POST':
        form = OpcionForm(request.POST)
        if form.is_valid():
            opcion = form.save(commit=False)
            opcion.pregunta = pregunta
            opcion.save()
            form.save_m2m()  # Guarda la relación ManyToMany con Media
            return redirect('lista_opciones', pregunta_id=pregunta.id) # Redirige a la lista de opciones
    else:
        form = OpcionForm()
    return render(request, 'core/crear_opcion.html', {'form': form, 'pregunta': pregunta})
def votaciones(request, pregunta_id, opcion_id):
    pregunta = get_object_or_404(Pregunta, pk=pregunta_id)
    opcion = get_object_or_404(Opcion, pk=opcion_id)
    
    if request.method == 'POST':
        form = FormularioForm(request.POST)
        if form.is_valid():
            try:
                voto = form.save(commit=False)
                voto.usuario = request.POST['nombre_twitch']
                voto.clean()
                voto.save()
                return render(
                    request,
                    'core/votacion.html',
                    {'form': FormularioForm(), 'mensaje': '¡Gracias por tu voto!', 'pregunta': pregunta, 'opcion': opcion, 'formulario':opcion}
                )
            except ValidationError as e:
                 form.add_error(None, e.message)
    else:
        initial_data = {'pregunta': pregunta, 'opcion': opcion}
        form = FormularioForm(initial=initial_data)

    return render(request, 'core/votacion.html', {'form': form, 'pregunta': pregunta, 'opcion': opcion, 'formulario':opcion})
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


def lista_preguntas(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    preguntas = Pregunta.objects.filter(encuesta=encuesta)
    return render(request, 'core/lista_preguntas.html', {'encuesta': encuesta, 'preguntas': preguntas})


def lista_opciones(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    opciones = Opcion.objects.filter(pregunta=pregunta)
    return render(request, 'core/lista_opciones.html', {'pregunta': pregunta, 'opciones': opciones})

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