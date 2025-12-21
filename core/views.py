from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from .forms import EncuestaForm, PreguntaForm, OpcionForm, FormularioForm, MediaForm
from .models import Encuesta, Pregunta, Opcion, Formulario, Media
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from difflib import SequenceMatcher
from rest_framework import viewsets
from .serializers import PreguntaSerializer, OpcionSerializer
import io
from openpyxl import Workbook
from django.http import HttpResponse
import pandas as pd
import os
from django.contrib import messages
from django.db.models import Prefetch
from django.utils.html import escape
import logging

logger = logging.getLogger(__name__)
@login_required
def inicio(request):
    """
    Muestra la interfaz de votación y maneja el inicio de sesión con nombre de usuario.
    Versión corregida con nombres de variables consistentes.
    """
    # 1. LÓGICA DEL FORMULARIO DE LOGIN (POST)
    if request.method == 'POST':
        # CORRECCIÓN: Cambiado de 'nombre_usuario' a 'nombre_twitch' para coincidir con el template
        nombre_twitch = request.POST.get('nombre_twitch', '').strip()
        
        # Validaciones mejoradas
        if not nombre_twitch:
            messages.error(request, "El nombre de usuario es requerido")
            return render(request, 'core/inicio.html', {'twitch_name': None})
        
        if len(nombre_twitch) < 3:
            messages.error(request, "El nombre debe tener al menos 3 caracteres")
            return render(request, 'core/inicio.html', {'twitch_name': None})
        
        if len(nombre_twitch) > 50:
            messages.error(request, "El nombre es demasiado largo (máximo 50 caracteres)")
            return render(request, 'core/inicio.html', {'twitch_name': None})
        
        # Sanitización básica
        nombre_twitch_limpio = escape(nombre_twitch)
        
        # CORRECCIÓN: Guardamos con la clave 'twitch_name' para coincidir con el template
        request.session['twitch_name'] = nombre_twitch_limpio
        request.session.modified = True
        
        messages.success(request, f"¡Bienvenido, {nombre_twitch_limpio}!")
        
        # Redirigimos a la misma vista (Patrón PRG - Post/Redirect/Get)
        return redirect('inicio')

    # 2. LÓGICA DE VISUALIZACIÓN (GET)
    # CORRECCIÓN: Cambiado de 'user_name' a 'twitch_name'
    twitch_name = request.session.get('twitch_name')
    
    # Obtenemos solo preguntas de encuestas activas con select_related
    preguntas = Pregunta.objects.filter(
        encuesta__estado='ACTIVA'
    ).select_related('encuesta').prefetch_related('opciones').order_by('id')
    
    total_preguntas = preguntas.count()
    
    # Caso especial: no hay preguntas activas
    if total_preguntas == 0:
        messages.info(request, "No hay encuestas activas en este momento")
        return render(request, 'core/inicio.html', {
            'preguntas': [],
            'twitch_name': twitch_name,
            'completed': False,
            'no_preguntas': True
        })
    
    # OPTIMIZACIÓN: Una sola consulta para obtener todos los votos del usuario
    votos_realizados = set()
    if twitch_name:
        votos_realizados = set(
            Formulario.objects.filter(
                pregunta__in=preguntas,
                usuario=twitch_name
            ).values_list('pregunta_id', flat=True)
        )
    
    # Construimos la lista de preguntas con información de voto
    preguntas_con_voto = []
    for pregunta in preguntas:
        ha_votado = pregunta.id in votos_realizados
        preguntas_con_voto.append({
            'pregunta': pregunta,
            'ha_votado': ha_votado
        })
    
    # Calculamos si ha completado todas las preguntas
    votos_usuario = len(votos_realizados)
    completed = (twitch_name is not None) and (votos_usuario == total_preguntas)
    
    # Calculamos el porcentaje de progreso
    progreso = 0
    if twitch_name and total_preguntas > 0:
        progreso = int((votos_usuario / total_preguntas) * 100)

    # 3. RENDERIZADO
    context = {
        'preguntas': preguntas_con_voto,
        'twitch_name': twitch_name,  # CORRECCIÓN: Cambiado de 'user_name'
        'completed': completed,
        'total_preguntas': total_preguntas,
        'votos_realizados': votos_usuario,
        'progreso': progreso,
    }
    
    return render(request, 'core/inicio.html', context)

@login_required
def votaciones(request, pregunta_id, opcion_id):
    """
    Maneja el proceso de votación con gestión de sesión de usuario.
    El usuario debe estar "logueado" (tener twitch_name en sesión).
    """
    # Obtener el nombre de usuario de la sesión
    twitch_name = request.session.get('twitch_name')
    
    # Si no hay usuario en sesión, redirigir al inicio para que haga login
    if not twitch_name:
        messages.error(request, "Debes iniciar sesión con tu nombre de Twitch primero.")
        return redirect('inicio')
    
    # Obtener la pregunta
    pregunta = get_object_or_404(Pregunta, pk=pregunta_id)
    
    # Verificar que la encuesta esté activa
    if pregunta.encuesta.estado != 'ACTIVA':
        messages.error(request, "Esta encuesta no está activa.")
        return redirect('inicio')
    
    # Verificar que la opción pertenece a la pregunta
    try:
        opcion = Opcion.objects.get(pk=opcion_id, pregunta=pregunta)
    except Opcion.DoesNotExist:
        messages.error(request, "La opción seleccionada no es válida.")
        return redirect('inicio')
    
    # Verificar si el usuario ya votó en esta pregunta
    if Formulario.objects.filter(pregunta=pregunta, usuario=twitch_name).exists():
        messages.warning(request, "Ya has votado en esta pregunta.")
        return redirect('inicio')
    
    # Manejar POST (envío del formulario)
    if request.method == 'POST':
        form = FormularioForm(request.POST, pregunta_id=pregunta_id)
        
        if form.is_valid():
            try:
                # Crear el voto pero no guardarlo todavía
                voto = form.save(commit=False)
                
                # Asignar el nombre de twitch
                voto.nombre_twitch = twitch_name
                # El modelo automáticamente hace: self.usuario = self.nombre_twitch
                
                # Guardar el voto
                voto.save()
                
                logger.info(f"Voto guardado: Usuario={twitch_name}, Pregunta={pregunta.id}, Opción={voto.opcion.opcion}")
                
                messages.success(request, f"¡Gracias por tu voto! Has votado por: {voto.opcion.opcion}")
                return redirect('inicio')
                
            except ValidationError as e:
                messages.error(request, str(e))
                logger.warning(f"Intento de voto duplicado: Usuario={twitch_name}, Pregunta={pregunta.id}")
            except Exception as e:
                logger.error(f"Error al guardar voto: {str(e)}")
                messages.error(request, f"Error al guardar el voto: {str(e)}")
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    # GET request - mostrar formulario con datos iniciales
    initial_data = {
        'pregunta': pregunta_id,
        'opcion': opcion_id,
    }
    
    form = FormularioForm(initial=initial_data, pregunta_id=pregunta_id)
    
    context = {
        'form': form,
        'pregunta': pregunta,
        'opcion': opcion,
        'twitch_name': twitch_name,
    }
    
    return render(request, 'core/votacion.html', context)

@login_required
def crear_encuesta(request):
    if request.method == 'POST':
        form = EncuestaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Encuesta creada exitosamente")
            return redirect('lista_encuestas')
    else:
        form = EncuestaForm()
    return render(request, 'crear/crear_encuesta.html', {'form': form})

@login_required
def lista_encuestas(request):
    encuestas = Encuesta.objects.filter(estado='ACTIVA')
    encuestas_terminadas = Encuesta.objects.filter(estado='TERMINADA')
    
    return render(request, 'listar/lista_encuestas.html', {
        'encuestas': encuestas, 
        'encuestas_terminadas': encuestas_terminadas
    })

@login_required
def editar_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    if request.method == 'POST':
        form = EncuestaForm(request.POST, instance=encuesta)
        if form.is_valid():
            form.save()
            messages.success(request, "Encuesta actualizada exitosamente")
            return redirect('lista_encuestas')
    else:
        form = EncuestaForm(instance=encuesta)
    return render(request, 'editar/editar_encuesta.html', {'form': form, 'encuesta': encuesta})

@login_required
def crear_pregunta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    if request.method == 'POST':
        form = PreguntaForm(request.POST)
        if form.is_valid():
            pregunta = form.save(commit=False)
            pregunta.encuesta = encuesta
            pregunta.save()
            messages.success(request, "Pregunta creada exitosamente")
            return redirect('lista_preguntas', encuesta_id=encuesta.id)
    else:
        form = PreguntaForm()
    return render(request, 'crear/crear_pregunta.html', {'form': form, 'encuesta': encuesta})

@login_required
def editar_pregunta(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    if request.method == 'POST':
        form = PreguntaForm(request.POST, instance=pregunta)
        if form.is_valid():
            form.save()
            messages.success(request, "Pregunta actualizada exitosamente")
            return redirect('lista_preguntas', encuesta_id=pregunta.encuesta.id)
    else:
        form = PreguntaForm(instance=pregunta)
    return render(request, 'editar/editar_pregunta.html', {'form': form, 'pregunta': pregunta})

@login_required
def crear_media(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    
    if request.method == 'POST':
        form = MediaForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                media = form.save(commit=False)
                media.pregunta = pregunta
                media.save()
                messages.success(request, "✅ Archivo multimedia agregado correctamente")
                return redirect('lista_medias', pregunta_id=pregunta.id)
            except Exception as e:
                messages.error(request, f"❌ Error al guardar: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"❌ {field}: {error}")
    else:
        form = MediaForm()
    
    return render(request, 'crear/crear_media.html', {
        'form': form,
        'pregunta': pregunta
    })

@login_required
def crear_opcion(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    if request.method == 'POST':
        form = OpcionForm(request.POST)
        if form.is_valid():
            opcion = form.save(commit=False)
            opcion.pregunta = pregunta
            opcion.save()
            messages.success(request, "Opción creada exitosamente")
            return redirect('lista_opciones', pregunta_id=pregunta.id)
    else:
        form = OpcionForm()
    return render(request, 'crear/crear_opcion.html', {'form': form, 'pregunta': pregunta})

@login_required
def resultados(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    preguntas = encuesta.preguntas.all().prefetch_related('opciones')
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

        resultados_por_pregunta.append({
            'pregunta': pregunta, 
            'resultados': resultados_opciones,
            'total_votos': total_votos
        })

    return render(request, 'core/resultados.html', {
        'encuesta': encuesta, 
        'resultados_por_pregunta': resultados_por_pregunta
    })

@login_required
def lista_preguntas(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    preguntas = Pregunta.objects.filter(encuesta=encuesta)
    return render(request, 'listar/lista_preguntas.html', {
        'encuesta': encuesta, 
        'preguntas': preguntas
    })

@login_required
def lista_opciones(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    opciones = Opcion.objects.filter(pregunta=pregunta)
    return render(request, 'listar/lista_opciones.html', {
        'pregunta': pregunta, 
        'opciones': opciones
    })

@login_required
def editar_opcion(request, opcion_id):
    opcion = get_object_or_404(Opcion, id=opcion_id)
    if request.method == 'POST':
        form = OpcionForm(request.POST, instance=opcion)
        if form.is_valid():
            form.save()
            messages.success(request, "Opción actualizada exitosamente")
            return redirect('lista_opciones', pregunta_id=opcion.pregunta.id)
    else:
        form = OpcionForm(instance=opcion)
    return render(request, 'editar/editar_opcion.html', {'form': form, 'opcion': opcion})

def mantenimiento(request):
    return render(request, 'core/mantenimiento.html')

def home(request):
    return render(request, 'core/home.html')

def logout_view(request):
    # Limpiar sesión de votación
    if 'user_name' in request.session:
        del request.session['user_name']
    # Cerrar sesión de autenticación
    logout(request)
    messages.info(request, "Has cerrado sesión exitosamente")
    return redirect('inicio')

def error_404(request, exception):
    return render(request, 'core/404.html', status=404)

@login_required
def eliminar_opcion(request, opcion_id):
    opcion = get_object_or_404(Opcion, id=opcion_id)
    pregunta_id = opcion.pregunta.id
    opcion.delete()
    messages.success(request, "Opción eliminada exitosamente")
    return redirect('lista_opciones', pregunta_id=pregunta_id)

@login_required
def eliminar_pregunta(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    encuesta_id = pregunta.encuesta.id
    pregunta.delete()
    messages.success(request, "Pregunta eliminada exitosamente")
    return redirect('lista_preguntas', encuesta_id=encuesta_id)

@login_required
def eliminar_encuesta(request, encuesta_id):
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    encuesta.delete()
    messages.success(request, "Encuesta eliminada exitosamente")
    return redirect('lista_encuestas')

@login_required
def lista_medias(request, pregunta_id):
    pregunta = get_object_or_404(Pregunta, id=pregunta_id)
    medias = Media.objects.filter(pregunta=pregunta).order_by('-fecha_creacion')
    
    # Pasar información sobre el tipo de cada media
    media_list = []
    for media in medias:
        media_dict = {
            'id': media.id,
            'nombre': media.nombre,
            'tipo_media': media.tipo_media,
            'archivo': media.archivo,
            'url_youtube': media.url_youtube,
            'fecha_creacion': media.fecha_creacion,
            'embed_url': None,
        }
        
        if media.tipo_media == 'YOUTUBE':
            media_dict['embed_url'] = media.get_youtube_embed_url()
        
        media_list.append(media_dict)
    
    return render(request, 'listar/lista_medias.html', {
        'pregunta': pregunta,
        'medias': media_list  # Pasar la lista procesada
    })

@login_required
def eliminar_media(request, media_id):
    media = get_object_or_404(Media, id=media_id)
    pregunta_id = media.pregunta.id
    
    try:
        # Si es un archivo local, eliminar el archivo físico
        if media.tipo_media == 'LOCAL' and media.archivo:
            if os.path.isfile(media.archivo.path):
                os.remove(media.archivo.path)
        
        media.delete()
        messages.success(request, "✅ Archivo multimedia eliminado correctamente")
    except Exception as e:
        messages.error(request, f"❌ Error al eliminar: {str(e)}")
    
    return redirect('lista_medias', pregunta_id=pregunta_id)

@login_required
def descargar_resultados(request, encuesta_id):
    """
    Genera y descarga un archivo Excel con los resultados de la votación.
    """
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    preguntas = encuesta.preguntas.prefetch_related('opciones').all()

    # Crear el archivo en memoria
    output = io.BytesIO()
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Resultados"

    # Encabezados de las columnas
    worksheet.append(["Pregunta", "Opción", "Votos Totales", "Porcentaje"])

    # Iterar sobre las preguntas
    for pregunta_obj in preguntas:
        opciones = pregunta_obj.opciones.all()
        
        total_votos_pregunta = Formulario.objects.filter(pregunta=pregunta_obj).count()

        for opcion_obj in opciones:
            votos_opcion = Formulario.objects.filter(
                pregunta=pregunta_obj, 
                opcion=opcion_obj
            ).count()
            
            if total_votos_pregunta > 0:
                porcentaje = (votos_opcion / total_votos_pregunta) * 100
            else:
                porcentaje = 0

            worksheet.append([
                pregunta_obj.pregunta,
                opcion_obj.opcion,
                votos_opcion,
                f"{round(porcentaje, 2)}%"
            ])
        
        worksheet.append([])

    # Guardar y preparar respuesta
    workbook.save(output)
    output.seek(0)

    filename = f"Resultados_{encuesta.titulo.replace(' ', '_')}.xlsx"

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def buscar_mejor_coincidencia(texto_buscado, lista_objetos, campo_comparar, umbral=0.8):
    """
    Busca en una lista de objetos Django cuál tiene el texto más parecido al buscado.
    Retorna el objeto si la similitud supera el umbral (0.0 a 1.0).
    """
    mejor_objeto = None
    mayor_similitud = 0.0
    texto_buscado = str(texto_buscado).lower().strip()

    for obj in lista_objetos:
        texto_obj = str(getattr(obj, campo_comparar)).lower().strip()
        similitud = SequenceMatcher(None, texto_buscado, texto_obj).ratio()

        if similitud > mayor_similitud:
            mayor_similitud = similitud
            mejor_objeto = obj

    if mayor_similitud >= umbral:
        return mejor_objeto
    return None

def comparar_resultados(request):
    encuestas = Encuesta.objects.all()
    
    if request.method == 'GET':
        return render(request, 'core/comparar_resultados.html', {
            'encuestas': encuestas
        })
    
    if request.method == 'POST' and request.FILES.get('archivo'):
        encuesta_id = request.POST.get('encuesta')
        
        if not encuesta_id:
            messages.error(request, "Debes seleccionar una encuesta actual para comparar.")
            return redirect('comparar_resultados')

        encuesta_actual = get_object_or_404(Encuesta, id=encuesta_id)
        archivo = request.FILES['archivo']

        try:
            df = pd.read_excel(archivo)
            df.columns = df.columns.str.strip()
        except Exception as e:
            messages.error(request, f"Error al leer el archivo Excel: {e}")
            return redirect('comparar_resultados')

        col_votos = 'Votos' if 'Votos' in df.columns else 'Votos Totales' if 'Votos Totales' in df.columns else None
        
        if not col_votos:
            messages.error(request, "El Excel debe tener una columna 'Votos' o 'Votos Totales'.")
            return redirect('comparar_resultados')

        if not {'Pregunta', 'Opción', 'Porcentaje'}.issubset(df.columns):
            messages.error(request, "El archivo falta columnas. Requiere: Pregunta, Opción, Votos, Porcentaje")
            return redirect('comparar_resultados')

        todas_preguntas_db = list(encuesta_actual.preguntas.all())
        comparacion_agrupada = {}

        for index, fila in df.iterrows():
            pregunta_txt_excel = str(fila['Pregunta']).strip()
            opcion_txt_excel = str(fila['Opción']).strip()
            
            try:
                votos_archivo = int(fila[col_votos])
            except:
                votos_archivo = 0

            try:
                porcentaje_archivo = float(str(fila['Porcentaje']).replace('%', '').strip())
            except:
                porcentaje_archivo = 0.0

            pregunta_db = buscar_mejor_coincidencia(
                pregunta_txt_excel, 
                todas_preguntas_db, 
                'pregunta', 
                umbral=0.7
            )

            if not pregunta_db:
                continue

            todas_opciones_pregunta = list(pregunta_db.opciones.all())
            opcion_db = buscar_mejor_coincidencia(
                opcion_txt_excel,
                todas_opciones_pregunta,
                'opcion',
                umbral=0.75
            )

            if not opcion_db:
                continue

            votos_reales = Formulario.objects.filter(pregunta=pregunta_db, opcion=opcion_db).count()
            total_votos_pregunta = Formulario.objects.filter(pregunta=pregunta_db).count()
            
            if total_votos_pregunta > 0:
                porcentaje_real = (votos_reales / total_votos_pregunta) * 100
            else:
                porcentaje_real = 0

            diferencia_votos = votos_reales - votos_archivo
            diferencia_porcentaje = porcentaje_real - porcentaje_archivo

            titulo_pregunta = pregunta_db.pregunta

            if titulo_pregunta not in comparacion_agrupada:
                comparacion_agrupada[titulo_pregunta] = {
                    'titulo': titulo_pregunta,
                    'opciones': [],
                    'total_votos_archivo': 0,
                    'total_votos_actual': 0
                }

            comparacion_agrupada[titulo_pregunta]['total_votos_archivo'] += votos_archivo
            comparacion_agrupada[titulo_pregunta]['total_votos_actual'] += votos_reales

            comparacion_agrupada[titulo_pregunta]['opciones'].append({
                'texto': opcion_db.opcion,
                'texto_antiguo': opcion_txt_excel,
                'votos_archivo': votos_archivo,
                'porcentaje_archivo': round(porcentaje_archivo, 1),
                'votos_actual': votos_reales,
                'porcentaje_actual': round(porcentaje_real, 1),
                'diferencia_votos': diferencia_votos,
                'diferencia_porcentaje': round(diferencia_porcentaje, 1),
                'crecimiento': diferencia_votos > 0,
                'igual': diferencia_votos == 0
            })

        lista_resultados = list(comparacion_agrupada.values())

        return render(request, 'core/comparar_resultados.html', {
            'encuestas': Encuesta.objects.all(),
            'resultados_agrupados': lista_resultados,
            'encuesta_seleccionada': encuesta_actual,
            'nombre_archivo': archivo.name
        })

    return render(request, 'core/comparar_resultados.html', {'encuestas': encuestas})

# REST Framework Viewsets
class PreguntaViewSet(viewsets.ModelViewSet):
    queryset = Pregunta.objects.all()
    serializer_class = PreguntaSerializer

class OpcionViewSet(viewsets.ModelViewSet):
    queryset = Opcion.objects.all()
    serializer_class = OpcionSerializer