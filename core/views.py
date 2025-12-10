from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError
from .forms import EncuestaForm, PreguntaForm, OpcionForm, FormularioForm, MediaForm
from .models import Encuesta, Pregunta, Opcion, Formulario, Media
from django.contrib import messages  # Import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from difflib import SequenceMatcher # Importante: Librería para comparar textos
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

#rest_framework
from rest_framework import viewsets
from .serializers import PreguntaSerializer, OpcionSerializer
import io
from openpyxl import Workbook
from django.http import HttpResponse
import pandas as pd
from django.shortcuts import render
from django.contrib import messages

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
    encuestas = Encuesta.objects.filter(estado='ACTIVA')
    encuestas_terminadas = Encuesta.objects.filter(estado='TERMINADA')
    
    return render(request, 'core/lista_encuestas.html', {'encuestas': encuestas, 'encuestas_terminadas': encuestas_terminadas})
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

@login_required
def eliminar_media(request, media_id):
    media = get_object_or_404(Media, id=media_id)
    pregunta_id = media.pregunta.id
    media.delete()
    return redirect('lista_medias', pregunta_id=pregunta_id)

@login_required
def descargar_resultados(request, encuesta_id):
    """
    Genera y descarga un archivo Excel con los resultados de la votación.
    """
    encuesta = get_object_or_404(Encuesta, id=encuesta_id)
    # Usamos prefetch_related para optimizar la base de datos y que cargue más rápido
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
        
        # Contamos cuántos formularios (votos) existen para esta pregunta específica
        total_votos_pregunta = Formulario.objects.filter(pregunta=pregunta_obj).count()

        for opcion_obj in opciones:
            # Contamos cuántos votos tiene esta opción específica
            votos_opcion = Formulario.objects.filter(pregunta=pregunta_obj, opcion=opcion_obj).count()
            
            # Calcular porcentaje evitando división por cero
            if total_votos_pregunta > 0:
                porcentaje = (votos_opcion / total_votos_pregunta) * 100
            else:
                porcentaje = 0

            # Escribir fila en Excel
            # CORRECCIÓN IMPORTANTE: Usamos .pregunta y .opcion (nombres reales de tus campos)
            # en lugar de .texto
            worksheet.append([
                pregunta_obj.pregunta,  # Antes decía .texto
                opcion_obj.opcion,      # Antes decía .texto
                votos_opcion,
                f"{round(porcentaje, 2)}%"
            ])
        
        # Agregamos una fila vacía entre preguntas para que se lea mejor
        worksheet.append([])

    # Guardar y preparar respuesta
    workbook.save(output)
    output.seek(0)

    # Limpiar el nombre del archivo para evitar errores con espacios
    filename = f"Resultados_{encuesta.titulo.replace(' ', '_')}.xlsx"

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# --- FUNCIÓN AUXILIAR PARA BUSCAR SIMILITUDES ---
def buscar_mejor_coincidencia(texto_buscado, lista_objetos, campo_comparar, umbral=0.8):
    """
    Busca en una lista de objetos Django cuál tiene el texto más parecido al buscado.
    Retorna el objeto si la similitud supera el umbral (0.0 a 1.0).
    """
    mejor_objeto = None
    mayor_similitud = 0.0
    texto_buscado = str(texto_buscado).lower().strip()

    for obj in lista_objetos:
        # Obtenemos el texto del objeto de la BD (ej: obj.pregunta o obj.opcion)
        texto_obj = str(getattr(obj, campo_comparar)).lower().strip()
        
        # Calculamos similitud (Ratio de 0 a 1)
        similitud = SequenceMatcher(None, texto_buscado, texto_obj).ratio()

        if similitud > mayor_similitud:
            mayor_similitud = similitud
            mejor_objeto = obj

    # Solo devolvemos si supera el umbral (ej: 80% de parecido)
    if mayor_similitud >= umbral:
        return mejor_objeto
    return None

# --- VISTA PRINCIPAL ---
def comparar_resultados(request):
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

        # Validaciones de columnas
        col_votos = 'Votos' if 'Votos' in df.columns else 'Votos Totales' if 'Votos Totales' in df.columns else None
        
        if not col_votos:
            messages.error(request, "El Excel debe tener una columna 'Votos' o 'Votos Totales'.")
            return redirect('comparar_resultados')

        if not {'Pregunta', 'Opción', 'Porcentaje'}.issubset(df.columns):
            messages.error(request, "El archivo falta columnas. Requiere: Pregunta, Opción, Votos, Porcentaje")
            return redirect('comparar_resultados')

        # Pre-cargar todas las preguntas de la encuesta actual para comparar rápido
        todas_preguntas_db = list(encuesta_actual.preguntas.all())

        comparacion_agrupada = {}

        for index, fila in df.iterrows():
            # Datos del Excel
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

            # ---------------------------------------------------------
            # PASO 1: Buscar Pregunta Similar (Fuzzy Matching)
            # ---------------------------------------------------------
            # Buscamos en 'todas_preguntas_db' cual se parece más a 'pregunta_txt_excel'
            pregunta_db = buscar_mejor_coincidencia(
                pregunta_txt_excel, 
                todas_preguntas_db, 
                'pregunta', 
                umbral=0.7 # 70% de similitud mínima para preguntas
            )

            if not pregunta_db:
                # Si no encontramos ninguna pregunta parecida, saltamos esta fila
                continue 

            # ---------------------------------------------------------
            # PASO 2: Buscar Opción Similar dentro de esa Pregunta
            # ---------------------------------------------------------
            todas_opciones_pregunta = list(pregunta_db.opciones.all())
            
            opcion_db = buscar_mejor_coincidencia(
                opcion_txt_excel,
                todas_opciones_pregunta,
                'opcion',
                umbral=0.75 # 75% de similitud para opciones (un poco más estricto)
            )

            if not opcion_db:
                continue

            # ---------------------------------------------------------
            # PASO 3: Cálculos (Igual que antes)
            # ---------------------------------------------------------
            votos_reales = Formulario.objects.filter(pregunta=pregunta_db, opcion=opcion_db).count()
            total_votos_pregunta = Formulario.objects.filter(pregunta=pregunta_db).count()
            
            if total_votos_pregunta > 0:
                porcentaje_real = (votos_reales / total_votos_pregunta) * 100
            else:
                porcentaje_real = 0

            diferencia_votos = votos_reales - votos_archivo
            diferencia_porcentaje = porcentaje_real - porcentaje_archivo

            # Usamos el texto REAL de la BD para el título, para que se vea limpio
            titulo_pregunta = pregunta_db.pregunta 

            if titulo_pregunta not in comparacion_agrupada:
                comparacion_agrupada[titulo_pregunta] = {
                    'titulo': titulo_pregunta,
                    'opciones': [],
                    'total_votos_archivo': 0,
                    'total_votos_actual': 0
                }

            comparacion_agrupada[titulo_pregunta]['total_votos_archivo'] += votos_archivo
            comparacion_agrupada[titulo_pregunta]['total_votos_actual'] += votos_reales # Nota: esto suma parciales

            comparacion_agrupada[titulo_pregunta]['opciones'].append({
                'texto': opcion_db.opcion, # Usamos el nombre actual de la opción
                'texto_antiguo': opcion_txt_excel, # Guardamos el nombre viejo por si quieres mostrarlo
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

    encuestas = Encuesta.objects.all()
    return render(request, 'core/comparar_resultados.html', {'encuestas': encuestas})

class PreguntaViewSet(viewsets.ModelViewSet):
    queryset = Pregunta.objects.all()
    serializer_class = PreguntaSerializer

class OpcionViewSet(viewsets.ModelViewSet):
    queryset = Opcion.objects.all()
    serializer_class = OpcionSerializer

