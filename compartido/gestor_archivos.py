import os
import configparser
import random
import shutil
from datetime import datetime


def leer_config_global():
    """
    Lee config_global.txt y retorna un diccionario con la configuración
    Similar al sistema de Marketplace pero adaptado para Facebook
    """
    import sys
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    archivo_config = os.path.join(base_dir, "config_global.txt")
    
    if not os.path.exists(archivo_config):
        print("⚠️  No existe config_global.txt. Creando configuración por defecto...")
        crear_config_defecto()
    
    config = configparser.RawConfigParser(delimiters=('=',))
    config.read(archivo_config, encoding='utf-8')
    
    # Convertir a diccionario con tipos correctos
    config_dict = {
        # [GENERAL]
        'nombre_proyecto': config['GENERAL']['nombre_proyecto'],
        'carpeta_mensajes': config['GENERAL']['carpeta_mensajes'],
        'navegador': config['GENERAL']['navegador'].lower(),
        'modo_debug': config['GENERAL']['modo_debug'].lower() == 'si',
        
        # [MODULOS]
        'modulo_facebook': config['MODULOS']['publicar_facebook'].lower() == 'si' if config.has_option('MODULOS', 'publicar_facebook') else True,
        'modulo_oraciones': config['MODULOS']['enviar_oraciones_whatsapp'].lower() == 'si' if config.has_option('MODULOS', 'enviar_oraciones_whatsapp') else False,
        'modulo_predicaciones': config['MODULOS']['extraer_predicaciones_whatsapp'].lower() == 'si' if config.has_option('MODULOS', 'extraer_predicaciones_whatsapp') else False,

        # [PUBLICACION]
        'tiempo_entre_intentos': int(config['PUBLICACION']['tiempo_entre_intentos']),
        'max_intentos_por_publicacion': int(config['PUBLICACION']['max_intentos_por_publicacion']),
        'espera_despues_publicar': int(config['PUBLICACION']['espera_despues_publicar']),
        'verificar_publicacion_exitosa': config['PUBLICACION']['verificar_publicacion_exitosa'].lower() == 'si',
        'espera_estabilizacion_modal': int(config['PUBLICACION']['espera_estabilizacion_modal']),
        
        # [LIMITES]
        'tiempo_minimo_entre_publicaciones_segundos': int(config['LIMITES']['tiempo_minimo_entre_publicaciones_segundos']),
        'permitir_duplicados': config['LIMITES']['permitir_duplicados'].lower() == 'si',
        'permitir_forzar_publicacion_manual': config['LIMITES']['permitir_forzar_publicacion_manual'].lower() == 'si',
        
        # [MENSAJES]
        'seleccion': _normalizar_seleccion(config['MENSAJES']['seleccion']),
        'relleno_hibrido': _normalizar_seleccion(config.get('MENSAJES', 'relleno_hibrido', fallback='aleatorio')),
        'cantidad_por_ejecucion': max(1, min(10, int(config.get('MENSAJES', 'cantidad_por_ejecucion', fallback='1')))),
        'historial_evitar_repetir': int(config['MENSAJES']['historial_evitar_repetir']),
        'formato_fecha': config['MENSAJES']['formato_fecha'].lower() == 'si',
        'agregar_hashtags': config['MENSAJES']['agregar_hashtags'].lower() == 'si',
        'hashtags': config['MENSAJES']['hashtags'],
        'agregar_firma': config['MENSAJES']['agregar_firma'].lower() == 'si',
        'texto_firma': config['MENSAJES']['texto_firma'],
        
        # [DEBUG]
        'modo_debug': config['DEBUG']['modo_debug'].lower(),
        
        # [NAVEGADOR]
        'usar_perfil_existente': config['NAVEGADOR']['usar_perfil_existente'].lower() == 'si',
        'carpeta_perfil_custom': config['NAVEGADOR']['carpeta_perfil_custom'],
        'desactivar_notificaciones': config['NAVEGADOR']['desactivar_notificaciones'].lower() == 'si',
        'maximizar_ventana': config['NAVEGADOR']['maximizar_ventana'].lower() == 'si',
        
        # [PREDICACIONES]
        'activar_predicaciones': config['PREDICACIONES']['activar_predicaciones'].lower() == 'si' if config.has_option('PREDICACIONES', 'activar_predicaciones') else False,
        'navegador_predicaciones': config['PREDICACIONES']['navegador'].split('#')[0].strip() if config.has_option('PREDICACIONES', 'navegador') else 'firefox',
        'usar_perfil_predicaciones': config['PREDICACIONES']['usar_perfil_existente'].split('#')[0].strip().lower() == 'si' if config.has_option('PREDICACIONES', 'usar_perfil_existente') else True,
        'alternar_con_predicaciones': config['PREDICACIONES']['alternar_con_predicaciones'].lower() == 'si' if config.has_option('PREDICACIONES', 'alternar_con_predicaciones') else False,
        'nombre_grupo_whatsapp': config['PREDICACIONES']['nombre_grupo_whatsapp'] if config.has_option('PREDICACIONES', 'nombre_grupo_whatsapp') else 'Prédicas',
        'mensajes_por_extraccion': int(config['PREDICACIONES']['mensajes_por_extraccion']) if config.has_option('PREDICACIONES', 'mensajes_por_extraccion') else 10,
        'agregar_introduccion_predica': config['PREDICACIONES']['agregar_introduccion_predica'].lower() == 'si' if config.has_option('PREDICACIONES', 'agregar_introduccion_predica') else True,
        'texto_introduccion_predica': config['PREDICACIONES']['texto_introduccion_predica'].replace('\\n', '\n') if config.has_option('PREDICACIONES', 'texto_introduccion_predica') else '🎬 Predicación recomendada:\n\n',
        'agregar_hashtags_predicaciones': config['PREDICACIONES']['agregar_hashtags_predicaciones'].lower() == 'si' if config.has_option('PREDICACIONES', 'agregar_hashtags_predicaciones') else True,
        'hashtags_predicaciones': config['PREDICACIONES']['hashtags_predicaciones'] if config.has_option('PREDICACIONES', 'hashtags_predicaciones') else '#Predicación,#Fe,#Cristiano'
    }
    
    return config_dict


def crear_config_defecto():
    """Crea config_global.txt con valores por defecto si no existe"""
    print("⚠️  Función crear_config_defecto() no implementada aún")
    print("   Por favor, copia manualmente el archivo config_global.txt al proyecto")


def verificar_y_crear_estructura():
    config = leer_config_global()
    base = _base_dir()

    carpetas_necesarias = [
        os.path.join(base, config['carpeta_mensajes']),
        os.path.join(base, 'cola-facebook'),
        os.path.join(base, 'cola-facebook', 'pendientes'),
        os.path.join(base, 'cola-facebook', 'publicados')
    ]

    if not config['usar_perfil_existente']:
        carpetas_necesarias.append(os.path.join(base, config['carpeta_perfil_custom']))

    carpetas_creadas = []
    for carpeta in carpetas_necesarias:
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)
            carpetas_creadas.append(carpeta)

    gitkeep_pendientes = os.path.join(base, 'cola-facebook', 'pendientes', '.gitkeep')
    gitkeep_publicados = os.path.join(base, 'cola-facebook', 'publicados', '.gitkeep')

    if not os.path.exists(gitkeep_pendientes):
        with open(gitkeep_pendientes, 'w') as f:
            f.write('')

    if not os.path.exists(gitkeep_publicados):
        with open(gitkeep_publicados, 'w') as f:
            f.write('')

    if carpetas_creadas:
        print(f"✅ Carpetas creadas: {', '.join(carpetas_creadas)}")

    return True


def _base_dir():
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def escribir_estado_predicaciones():
    """Escribe en estado_predicaciones.json el conteo real de pendientes"""
    import json
    base = _base_dir()
    pendientes = contar_predicaciones_pendientes()
    publicados = contar_predicaciones_publicadas()
    estado = {
        'pendientes': pendientes,
        'publicados': publicados
    }
    ruta = os.path.join(base, 'estado_predicaciones.json')
    try:
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump(estado, f, indent=2)
    except Exception as e:
        print(f"⚠️  No se pudo escribir estado: {e}")


def leer_estado_predicaciones():
    """Lee estado_predicaciones.json — si no existe cuenta directamente la carpeta"""
    import json
    base = _base_dir()
    ruta = os.path.join(base, 'estado_predicaciones.json')
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {
            'pendientes': contar_predicaciones_pendientes(),
            'publicados': contar_predicaciones_publicadas()
        }


def contar_predicaciones_pendientes():
    carpeta = os.path.join(_base_dir(), 'cola-facebook', 'pendientes')
    if not os.path.exists(carpeta):
        return 0
    archivos = [f for f in os.listdir(carpeta)
                if f.endswith('.txt') and f.startswith('predica-')]
    return len(archivos)


def contar_predicaciones_publicadas():
    carpeta = os.path.join(_base_dir(), 'cola-facebook', 'publicados')
    if not os.path.exists(carpeta):
        return 0
    archivos = [f for f in os.listdir(carpeta)
                if f.endswith('.txt') and f.startswith('predica-')]
    return len(archivos)


def obtener_siguiente_predicacion():
    carpeta = os.path.join(_base_dir(), 'cola-facebook', 'pendientes')

    if not os.path.exists(carpeta):
        return None, None

    archivos = [f for f in os.listdir(carpeta)
                if f.endswith('.txt') and f.startswith('predica-')]

    if not archivos:
        return None, None

    archivos.sort()
    archivo_siguiente = archivos[0]
    ruta_completa = os.path.join(carpeta, archivo_siguiente)

    return ruta_completa, archivo_siguiente


def mover_predicacion_a_publicados(nombre_archivo):
    base = _base_dir()
    carpeta_pendientes = os.path.join(base, 'cola-facebook', 'pendientes')
    carpeta_publicados = os.path.join(base, 'cola-facebook', 'publicados')

    os.makedirs(carpeta_publicados, exist_ok=True)

    origen_txt = os.path.join(carpeta_pendientes, nombre_archivo)
    destino_txt = os.path.join(carpeta_publicados, nombre_archivo)

    try:
        if os.path.exists(origen_txt):
            shutil.move(origen_txt, destino_txt)
            print(f"   📦 Movido: {nombre_archivo}")

        nombre_base = nombre_archivo.replace('.txt', '')
        origen_img = os.path.join(carpeta_pendientes, f"{nombre_base}.jpg")
        destino_img = os.path.join(carpeta_publicados, f"{nombre_base}.jpg")

        if os.path.exists(origen_img):
            shutil.move(origen_img, destino_img)
            print(f"   🖼️  Movida imagen: {nombre_base}.jpg")

        return True

    except Exception as e:
        print(f"   ⚠️  Error moviendo predicación: {e}")
        return False


def obtener_mensaje_aleatorio_sin_repetir(registro_publicaciones):
    """
    Obtiene un mensaje aleatorio evitando los últimos N publicados
    
    Args:
        registro_publicaciones: Diccionario con historial de publicaciones
        
    Returns:
        tuple: (contenido_mensaje, nombre_archivo) o (None, None) si no hay mensajes
    """
    config = leer_config_global()
    carpeta = os.path.join(_base_dir(), config['carpeta_mensajes'])
    
    # Verificar que exista la carpeta
    if not os.path.exists(carpeta):
        print(f"❌ No existe la carpeta: {carpeta}")
        return None, None
    
    # Obtener todos los archivos .txt
    todos_mensajes = [f for f in os.listdir(carpeta) if f.endswith('.txt')]
    
    if not todos_mensajes:
        print(f"❌ No hay archivos .txt en la carpeta: {carpeta}")
        return None, None
    
    print(f"📦 Total de mensajes disponibles: {len(todos_mensajes)}")
    
    # Obtener historial de últimos N mensajes
    historial_reciente = registro_publicaciones.get('historial_reciente', [])
    limite_historial = config['historial_evitar_repetir']
    
    # Mensajes bloqueados (últimos N publicados)
    mensajes_bloqueados = historial_reciente[-limite_historial:] if historial_reciente else []
    
    # Mensajes disponibles (no están en el historial reciente)
    mensajes_disponibles = [m for m in todos_mensajes if m not in mensajes_bloqueados]
    
    print(f"🚫 Mensajes bloqueados (últimos {limite_historial}): {len(mensajes_bloqueados)}")
    print(f"✅ Mensajes disponibles: {len(mensajes_disponibles)}")
    
    # Si no hay mensajes disponibles, usar todos (caso extremo)
    if not mensajes_disponibles:
        print("⚠️  No hay mensajes disponibles. Usando todos los mensajes.")
        mensajes_disponibles = todos_mensajes
    
    # Mostrar mensajes bloqueados en debug
    if mensajes_bloqueados and config['modo_debug'] in ['detallado', 'completo']:
        print(f"\n🚫 Bloqueados actualmente:")
        for i, msg in enumerate(mensajes_bloqueados, 1):
            print(f"   {i}. {msg}")
    
    # Seleccionar uno aleatorio de los disponibles
    mensaje_seleccionado = random.choice(mensajes_disponibles)
    
    print(f"\n🎲 Mensaje seleccionado: {mensaje_seleccionado}")
    
    # Leer contenido del mensaje
    ruta_mensaje = os.path.join(carpeta, mensaje_seleccionado)
    try:
        with open(ruta_mensaje, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()
        
        # Aplicar transformaciones según config
        contenido = aplicar_transformaciones_mensaje(contenido, config)
        
        return contenido, mensaje_seleccionado
    
    except Exception as e:
        print(f"❌ Error leyendo mensaje {mensaje_seleccionado}: {e}")
        return None, None


def obtener_mensaje_secuencial(registro_publicaciones):
    """
    Obtiene el siguiente mensaje en orden alfabético
    
    Args:
        registro_publicaciones: Diccionario con historial de publicaciones
        
    Returns:
        tuple: (contenido_mensaje, nombre_archivo) o (None, None) si no hay mensajes
    """
    config = leer_config_global()
    carpeta = os.path.join(_base_dir(), config['carpeta_mensajes'])
    
    # Verificar que exista la carpeta
    if not os.path.exists(carpeta):
        print(f"❌ No existe la carpeta: {carpeta}")
        return None, None
    
    # Obtener todos los archivos .txt ordenados
    todos_mensajes = sorted([f for f in os.listdir(carpeta) if f.endswith('.txt')])
    
    if not todos_mensajes:
        print(f"❌ No hay archivos .txt en la carpeta: {carpeta}")
        return None, None
    
    # Obtener el último mensaje publicado
    historial = registro_publicaciones.get('historial_completo', [])
    
    if not historial:
        # Primera publicación, usar el primero
        mensaje_seleccionado = todos_mensajes[0]
    else:
        # Obtener el último publicado (solo bíblicos)
        ultimo_biblico = None
        for entrada in reversed(historial):
            if entrada.get('tipo', 'biblico') == 'biblico':
                ultimo_biblico = entrada.get('mensaje_archivo')
                break
        
        if not ultimo_biblico:
            # No hay bíblicos previos, empezar desde el primero
            mensaje_seleccionado = todos_mensajes[0]
        else:
            try:
                # Encontrar índice del último publicado
                indice_actual = todos_mensajes.index(ultimo_biblico)
                # Siguiente mensaje (con rotación)
                indice_siguiente = (indice_actual + 1) % len(todos_mensajes)
                mensaje_seleccionado = todos_mensajes[indice_siguiente]
            except ValueError:
                # Si el último publicado no existe, empezar desde el primero
                mensaje_seleccionado = todos_mensajes[0]
    
    print(f"📋 Mensaje secuencial seleccionado: {mensaje_seleccionado}")
    
    # Leer contenido
    ruta_mensaje = os.path.join(carpeta, mensaje_seleccionado)
    try:
        with open(ruta_mensaje, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()
        
        # Aplicar transformaciones
        contenido = aplicar_transformaciones_mensaje(contenido, config)
        
        return contenido, mensaje_seleccionado
    
    except Exception as e:
        print(f"❌ Error leyendo mensaje {mensaje_seleccionado}: {e}")
        return None, None


def aplicar_transformaciones_mensaje(contenido, config):
    """
    Aplica transformaciones al mensaje según configuración
    (fecha, hashtags, firma, etc.)
    
    Args:
        contenido: Texto del mensaje original
        config: Diccionario de configuración
        
    Returns:
        str: Mensaje transformado
    """
    mensaje_final = contenido
    
    # Agregar fecha
    if config['formato_fecha']:
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        mensaje_final = f"{mensaje_final}\n\n📅 {fecha_actual}"
    
    # Agregar hashtags
    if config['agregar_hashtags'] and config['hashtags']:
        mensaje_final = f"{mensaje_final}\n\n{config['hashtags']}"
    
    # Agregar firma
    if config['agregar_firma'] and config['texto_firma']:
        mensaje_final = f"{mensaje_final}\n\n{config['texto_firma']}"
    
    return mensaje_final


def _normalizar_seleccion(valor):
    valor = (valor or '').strip().lower()
    equivalencias = {
        'aleatoria': 'aleatorio',
        'secuencia': 'secuencial',
        'elegido': 'elegidos',
        'hibrida': 'hibrido',
        'híbrido': 'hibrido',
    }
    valor = equivalencias.get(valor, valor)
    if valor not in ('aleatorio', 'secuencial', 'elegidos', 'hibrido'):
        return 'aleatorio'
    return valor


def _ruta_mensajes_elegidos():
    return os.path.join(_base_dir(), 'mensajes_elegidos.json')


def leer_mensajes_elegidos():
    """Retorna la cola de mensajes elegidos manualmente, en orden de publicación"""
    import json
    ruta = _ruta_mensajes_elegidos()
    if not os.path.exists(ruta):
        return []
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            datos = json.load(f)
        return [m for m in datos.get('elegidos', []) if isinstance(m, str)]
    except Exception as e:
        print(f"⚠️  Error leyendo mensajes elegidos: {e}")
        return []


def guardar_mensajes_elegidos(lista):
    import json
    ruta = _ruta_mensajes_elegidos()
    sin_duplicados = list(dict.fromkeys(lista))
    try:
        with open(ruta, 'w', encoding='utf-8') as f:
            json.dump({'elegidos': sin_duplicados}, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️  Error guardando mensajes elegidos: {e}")
        return False


def quitar_mensaje_elegido(nombre_archivo):
    elegidos = leer_mensajes_elegidos()
    if nombre_archivo in elegidos:
        elegidos.remove(nombre_archivo)
        guardar_mensajes_elegidos(elegidos)


def _leer_mensaje_transformado(carpeta, nombre_archivo, config):
    ruta = os.path.join(carpeta, nombre_archivo)
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()
        return aplicar_transformaciones_mensaje(contenido, config)
    except Exception as e:
        print(f"❌ Error leyendo mensaje {nombre_archivo}: {e}")
        return None


def _rellenar_aleatorio(todos, ya_elegidos, cantidad, registro_publicaciones, config):
    limite = config['historial_evitar_repetir']
    historial_reciente = registro_publicaciones.get('historial_reciente', [])
    bloqueados = set(historial_reciente[-limite:]) if limite > 0 else set()

    candidatos = [m for m in todos if m not in ya_elegidos and m not in bloqueados]
    random.shuffle(candidatos)
    seleccion = candidatos[:cantidad]

    if len(seleccion) < cantidad:
        # Si la memoria bloquea demasiados, se permite repetir antes que publicar menos
        reserva = [m for m in todos if m not in ya_elegidos and m not in seleccion]
        random.shuffle(reserva)
        seleccion += reserva[:cantidad - len(seleccion)]

    return seleccion


def _rellenar_secuencial(todos, ya_elegidos, cantidad, registro_publicaciones):
    ultimo_biblico = None
    for entrada in reversed(registro_publicaciones.get('historial_completo', [])):
        if entrada.get('tipo', 'biblico') == 'biblico':
            ultimo_biblico = entrada.get('mensaje_archivo')
            break

    inicio = 0
    if ultimo_biblico in todos:
        inicio = (todos.index(ultimo_biblico) + 1) % len(todos)

    seleccion = []
    for i in range(len(todos)):
        nombre = todos[(inicio + i) % len(todos)]
        if nombre in ya_elegidos:
            continue
        seleccion.append(nombre)
        if len(seleccion) >= cantidad:
            break

    return seleccion


def obtener_mensajes_a_publicar(registro_publicaciones, config, cantidad=None):
    """
    Arma la lista de mensajes bíblicos a publicar en esta ejecución.

    Primero toma la cola de elegidos (modos 'elegidos' e 'hibrido') y luego
    completa hasta 'cantidad' con aleatorio o secuencial según el modo.

    Returns:
        list[dict]: [{'nombre': str, 'contenido': str, 'elegido': bool}, ...]
    """
    carpeta = os.path.join(_base_dir(), config['carpeta_mensajes'])
    if not os.path.exists(carpeta):
        print(f"❌ No existe la carpeta: {carpeta}")
        return []

    todos = sorted([f for f in os.listdir(carpeta) if f.endswith('.txt')])
    if not todos:
        print(f"❌ No hay archivos .txt en la carpeta: {carpeta}")
        return []

    modo = config['seleccion']
    cantidad = cantidad or config['cantidad_por_ejecucion']

    elegidos = []
    if modo in ('elegidos', 'hibrido'):
        cola = leer_mensajes_elegidos()
        inexistentes = [m for m in cola if m not in todos]
        if inexistentes:
            print(f"⚠️  Elegidos que ya no existen (se ignoran): {', '.join(inexistentes)}")
        elegidos = [m for m in cola if m in todos][:cantidad]

    faltantes = cantidad - len(elegidos)
    relleno = []
    tipo_relleno = None
    if faltantes > 0:
        if modo in ('aleatorio', 'secuencial'):
            tipo_relleno = modo
        elif modo == 'hibrido':
            tipo_relleno = config['relleno_hibrido'] if config['relleno_hibrido'] in ('aleatorio', 'secuencial') else 'aleatorio'

        if tipo_relleno == 'aleatorio':
            relleno = _rellenar_aleatorio(todos, elegidos, faltantes, registro_publicaciones, config)
        elif tipo_relleno == 'secuencial':
            relleno = _rellenar_secuencial(todos, elegidos, faltantes, registro_publicaciones)

    print(f"📦 Total de mensajes disponibles: {len(todos)}")
    print(f"🎯 Modo: {modo}" + (f" (relleno {config['relleno_hibrido']})" if modo == 'hibrido' else ''))
    print(f"🔢 Cantidad por ejecución: {cantidad}")

    resultado = []
    for nombre in elegidos + relleno:
        contenido = _leer_mensaje_transformado(carpeta, nombre, config)
        if contenido:
            resultado.append({'nombre': nombre, 'contenido': contenido, 'elegido': nombre in elegidos})

    for i, m in enumerate(resultado, 1):
        marca = "📌" if m['elegido'] else ("📋" if tipo_relleno == 'secuencial' else "🎲")
        print(f"   {i}. {marca} {m['nombre']}")

    if modo == 'elegidos' and not resultado:
        print("📭 No hay mensajes elegidos en cola")

    return resultado


MODULOS_DISPONIBLES = [
    ("biblico",          "▶️  Publicar Mensaje Bíblico en Facebook"),
    ("extraer",          "🎬  Extraer Predicaciones de WhatsApp"),
    ("publicar_predica", "📤  Publicar Prédica Extraída en Facebook"),
    ("oraciones",        "📱  Enviar Oraciones por WhatsApp"),
]


def id_tarea(nombre):
    """Convierte el nombre de una tarea en un id sin espacios ni acentos, seguro para la línea de comandos"""
    import re
    import unicodedata
    sin_acentos = unicodedata.normalize('NFKD', nombre).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^A-Za-z0-9]+', '_', sin_acentos).strip('_') or 'Tarea'


def _ruta_tareas_programadas():
    return os.path.join(_base_dir(), 'tareas_programadas.json')


def leer_tareas_programadas():
    """Retorna {id_tarea: config} con la configuración propia de cada tarea automática"""
    import json
    ruta = _ruta_tareas_programadas()
    if not os.path.exists(ruta):
        return {}
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f).get('tareas', {})
    except Exception as e:
        print(f"⚠️  Error leyendo tareas programadas: {e}")
        return {}


def _guardar_tareas_programadas(tareas):
    import json
    try:
        with open(_ruta_tareas_programadas(), 'w', encoding='utf-8') as f:
            json.dump({'tareas': tareas}, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"⚠️  Error guardando tareas programadas: {e}")
        return False


def obtener_config_tarea(id_de_tarea):
    """
    Retorna la configuración de una tarea o None si no tiene.

    Formato: {'nombre': str, 'modulos': [str], 'destinatarios': None | [{'nombre', 'tipo', 'mensaje_asignado'}]}
    destinatarios None significa usar los destinatarios por defecto.
    """
    return leer_tareas_programadas().get(id_de_tarea)


def guardar_config_tarea(id_de_tarea, nombre, modulos, destinatarios=None):
    tareas = leer_tareas_programadas()
    tareas[id_de_tarea] = {
        'nombre': nombre,
        'modulos': [m for m in modulos if m in dict(MODULOS_DISPONIBLES)],
        'destinatarios': destinatarios
    }
    return _guardar_tareas_programadas(tareas)


def eliminar_config_tarea(id_de_tarea):
    tareas = leer_tareas_programadas()
    if id_de_tarea in tareas:
        del tareas[id_de_tarea]
        _guardar_tareas_programadas(tareas)


PREFIJO_TAREAS = "AutomaPro_MensajesBiblicos"


def id_de_nombre_tarea(nombre):
    """Id en tareas_programadas.json a partir del nombre de la tarea en Windows"""
    n = nombre[1:] if nombre.startswith('\\') else nombre
    if n.startswith(PREFIJO_TAREAS + "_"):
        n = n[len(PREFIJO_TAREAS) + 1:]
    return id_tarea(n)


def modulos_secuencia_general():
    """Módulos activos de [SECUENCIA] en config_global.txt (lo que hacían las tareas antiguas)"""
    cfg = configparser.RawConfigParser(delimiters=('=',))
    cfg.read(os.path.join(_base_dir(), "config_global.txt"), encoding='utf-8')
    modulos = cfg.get('SECUENCIA', 'modulos_activos', fallback='biblico,extraer,publicar_predica')
    return [m.strip() for m in modulos.split(',') if m.strip()]


def _comando_de_tarea_windows(nombre):
    """Comando que ejecuta una tarea de Windows, o '' si no se pudo leer"""
    import subprocess
    try:
        resultado = subprocess.run(
            ['schtasks', '/Query', '/TN', nombre, '/FO', 'LIST', '/V'],
            capture_output=True, text=True, encoding='cp850', errors='ignore',
            stdin=subprocess.DEVNULL, timeout=20,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        )
    except Exception:
        return ''
    for linea in resultado.stdout.split('\n'):
        if ':' in linea:
            clave, valor = linea.split(':', 1)
            if 'Tarea que se ejecutar' in clave or 'Task To Run' in clave:
                return valor.strip()
    return ''


def migrar_tareas_antiguas():
    """
    Agrega --tarea al comando de las tareas creadas antes de esta versión, sin tocar sus días ni su hora,
    para que nunca se ejecuten por el camino del doble clic (que puede quedarse esperando una respuesta).
    Conserva el ejecutable que ya tenían. Retorna cuántas tareas convirtió.
    """
    import subprocess
    sin_ventana = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    try:
        lista = subprocess.run(
            ['schtasks', '/Query', '/FO', 'CSV', '/NH'],
            capture_output=True, text=True, encoding='cp850', errors='ignore',
            stdin=subprocess.DEVNULL, timeout=30, creationflags=sin_ventana
        )
    except Exception as e:
        print(f"⚠️  No se pudieron consultar las tareas: {e}")
        return 0

    nombres = []
    for linea in lista.stdout.splitlines():
        nombre = linea.split('","')[0].strip().strip('"')
        if PREFIJO_TAREAS in nombre:
            nombres.append(nombre.split('\\')[-1])

    migradas = 0
    for nombre in nombres:
        comando_actual = _comando_de_tarea_windows(nombre)
        if not comando_actual or '--tarea' in comando_actual:
            continue

        id_de_tarea = id_de_nombre_tarea(nombre)
        if comando_actual.lower().startswith('cmd /c') and comando_actual.endswith('"'):
            comando_nuevo = f'{comando_actual[:-1]} --tarea={id_de_tarea}"'
        else:
            comando_nuevo = f'{comando_actual} --tarea={id_de_tarea}'

        try:
            resultado = subprocess.run(
                ['schtasks', '/Change', '/TN', nombre, '/TR', comando_nuevo],
                capture_output=True, text=True, stdin=subprocess.DEVNULL,
                timeout=20, creationflags=sin_ventana
            )
        except Exception as e:
            print(f"⚠️  No se pudo actualizar la tarea {nombre}: {e}")
            continue

        if resultado.returncode == 0:
            if not obtener_config_tarea(id_de_tarea):
                guardar_config_tarea(id_de_tarea, nombre, modulos_secuencia_general())
            migradas += 1
        else:
            print(f"⚠️  No se pudo actualizar la tarea {nombre}: {resultado.stderr.strip()}")

    return migradas


def registrar_evento_tarea(id_de_tarea, texto):
    """Agrega una línea a registro_tareas.log para revisar después qué pasó en una ejecución automática"""
    linea = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {id_de_tarea}  {texto}\n"
    try:
        with open(os.path.join(_base_dir(), 'registro_tareas.log'), 'a', encoding='utf-8') as f:
            f.write(linea)
    except Exception as e:
        print(f"⚠️  No se pudo escribir en registro_tareas.log: {e}")


def obtener_ruta_perfil_navegador():
    """
    Obtiene la ruta del perfil del navegador según configuración
    
    Returns:
        str: Ruta al perfil o None si usa perfil existente del sistema
    """
    config = leer_config_global()
    
    if config['usar_perfil_existente']:
        # Detectar perfil según navegador
        if config['navegador'] == 'firefox':
            return obtener_primer_perfil_firefox()
        elif config['navegador'] == 'chrome':
            # Chrome usa perfil del sistema por defecto
            return None
        else:
            print(f"⚠️  Navegador desconocido: {config['navegador']}")
            return None
    else:
        # Usar carpeta de perfil personalizada
        carpeta_perfil = os.path.join(_base_dir(), config['carpeta_perfil_custom'])
        
        # Crear carpeta si no existe
        if not os.path.exists(carpeta_perfil):
            os.makedirs(carpeta_perfil)
            print(f"✅ Carpeta de perfil creada: {carpeta_perfil}")
        
        return os.path.abspath(carpeta_perfil)


def obtener_primer_perfil_firefox():
    """
    Encuentra automáticamente el primer perfil de Firefox disponible
    
    Returns:
        str: Ruta al perfil de Firefox o None si no se encuentra
    """
    ruta_perfiles = os.path.expanduser("~\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles")
    
    if not os.path.exists(ruta_perfiles):
        print(f"⚠️  No se encontró la carpeta de perfiles de Firefox: {ruta_perfiles}")
        return None
    
    perfiles = [f for f in os.listdir(ruta_perfiles) if os.path.isdir(os.path.join(ruta_perfiles, f))]
    
    if not perfiles:
        print("⚠️  No se encontraron perfiles de Firefox")
        return None
    
    perfil_seleccionado = os.path.join(ruta_perfiles, perfiles[0])
    print(f"🦊 Perfil Firefox detectado: {perfiles[0]}")
    return perfil_seleccionado


def obtener_estadisticas_mensajes():
    """
    Obtiene estadísticas sobre los mensajes disponibles
    
    Returns:
        dict: Estadísticas de mensajes
    """
    config = leer_config_global()
    carpeta = os.path.join(_base_dir(), config['carpeta_mensajes'])
    
    if not os.path.exists(carpeta):
        return {
            'total_mensajes': 0,
            'mensajes_validos': [],
            'existe_carpeta': False
        }
    
    todos_archivos = os.listdir(carpeta)
    mensajes_txt = [f for f in todos_archivos if f.endswith('.txt')]
    
    return {
        'total_mensajes': len(mensajes_txt),
        'mensajes_validos': sorted(mensajes_txt),
        'existe_carpeta': True,
        'ruta_carpeta': os.path.abspath(carpeta)
    }


def guardar_nombre_grupo_whatsapp(nombre_grupo):
    """Guarda el nombre del grupo de WhatsApp en config_global.txt"""
    import configparser
    
    import sys
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    archivo_config = os.path.join(base_dir, "config_global.txt")
    config = configparser.RawConfigParser(delimiters=('=',))
    config.read(archivo_config, encoding='utf-8')
    
    if not config.has_section('PREDICACIONES'):
        config.add_section('PREDICACIONES')
    
    config.set('PREDICACIONES', 'nombre_grupo_whatsapp', nombre_grupo)
    
    try:
        with open(archivo_config, 'w', encoding='utf-8') as f:
            config.write(f)
        return True
    except Exception as e:
        print(f"❌ Error guardando nombre del grupo: {e}")
        return False