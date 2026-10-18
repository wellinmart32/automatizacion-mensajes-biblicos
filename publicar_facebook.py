import sys
import time
import os
import ctypes
import configparser

# ── Colores ANSI ──────────────────────────────────────────────
V  = '\033[92m'   # verde
R  = '\033[91m'   # rojo
A  = '\033[93m'   # amarillo
C  = '\033[96m'   # cian
N  = '\033[1m'    # negrita
X  = '\033[0m'    # reset
# ─────────────────────────────────────────────────────────────

from datetime import datetime
from compartido.gestor_archivos import (
    leer_config_global,
    verificar_y_crear_estructura,
    obtener_mensajes_a_publicar,
    quitar_mensaje_elegido,
    obtener_config_tarea,
    registrar_evento_tarea,
    MODULOS_DISPONIBLES,
    contar_predicaciones_pendientes,
    obtener_siguiente_predicacion,
    mover_predicacion_a_publicados
)
from publicadores.publicador_facebook import PublicadorFacebook
from gestor_registro import GestorRegistro
from gestor_licencias import GestorLicencias
from dialogos_licencia import DialogosLicencia

def verificar_licencia_inicio():
    gestor_lic = GestorLicencias("MensajesBiblicos")
    resultado = gestor_lic.verificar_e_iniciar()

    if not resultado.get('valida'):
        return None

    # Verificar expiración para TRIAL
    if resultado.get('tipo') == 'TRIAL':
        dias = resultado.get('diasRestantes', 0)
        if dias is not None and dias <= 0:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning(
                "⏰ Período de Prueba Expirado",
                "Tu período de prueba ha terminado.\n\n"
                "Adquiere la versión Completa para seguir publicando.\n\n"
                "Visita: automapro-frontend.vercel.app"
            )
            root.destroy()
            return None
        print(f"\n⚠️  MODO PRUEBA - Quedan {dias} días\n")

    if resultado.get('tipo') == 'FULL' or resultado.get('developer_permanente'):
        print("\n✅ Licencia completa activada - Todas las funciones desbloqueadas\n")

    return resultado


def mostrar_banner():
    print(f"\n{N}{C}" + "="*70 + X)
    print(f"{N}{C}" + " " * 15 + "🚀 PUBLICADOR AUTOMÁTICO DE FACEBOOK" + X)
    print(f"{N}{C}" + " " * 20 + "Sistema de Mensajes Bíblicos" + X)
    print(f"{N}{C}" + "="*70 + X + "\n")


def mostrar_configuracion(config):
    print("📁 Verificando estructura...")
    verificar_y_crear_estructura()
    print()
    print("⚙️  CONFIGURACIÓN DEL SISTEMA:")
    print(f"   📁 Carpeta mensajes: {config['carpeta_mensajes']}")
    print(f"   🌐 Navegador: {config['navegador'].upper()}")
    print(f"   🎲 Selección: {config['seleccion'].capitalize()}")
    print(f"   💾 Memoria: Últimos {config['historial_evitar_repetir']} mensajes")
    print(f"   🔢 Mensajes por ejecución: {config['cantidad_por_ejecucion']}")
    print(f"   🔄 Máx. intentos: {config.get('max_intentos_por_publicacion', 3)}")
    if config.get('activar_predicaciones'):
        print(f"   🎬 Predicaciones: ACTIVADAS")
        print(f"   📱 Grupo WhatsApp: {config['nombre_grupo_whatsapp']}")
    print()


def publicar_con_reintentos(publicador, contenido, tipo_publicacion, config, gestor, nombre_archivo=None):
    max_intentos = config.get('max_intentos_por_publicacion', 3)
    tiempo_entre_intentos = config.get('tiempo_entre_intentos', 10)

    for intento in range(1, max_intentos + 1):
        try:
            print(f"\n{'='*70}")
            print(f"🔄 INTENTO {intento} DE {max_intentos}")
            print(f"{'='*70}\n")
            exito = publicador.publicar_completo(contenido)
            if exito:
                print(f"✅ Publicación exitosa en intento {intento}")
                return True
            else:
                print(f"⚠️  Intento {intento} falló")
                if intento < max_intentos:
                    print(f"⏳ Esperando {tiempo_entre_intentos}s antes de reintentar...")
                    time.sleep(tiempo_entre_intentos)
        except Exception as e:
            print(f"❌ Error en intento {intento}: {e}")
            if intento < max_intentos:
                print(f"⏳ Esperando {tiempo_entre_intentos}s antes de reintentar...")
                time.sleep(tiempo_entre_intentos)
            else:
                import traceback
                traceback.print_exc()

    return False


def _publicar_mensaje_biblico(config):
    gestor = GestorRegistro()
    gestor.mostrar_estadisticas()
    gestor.mostrar_historial_reciente(5)

    tiempo_minimo = config['tiempo_minimo_entre_publicaciones_segundos']
    puede, motivo = gestor.puede_publicar_ahora(tiempo_minimo, config['permitir_forzar_publicacion_manual'])
    print(f"\n⏱️  {motivo}")
    if not puede:
        print(f"{A}⚠️  Aún no se cumple el tiempo mínimo entre publicaciones{X}")
        return

    mensajes = obtener_mensajes_a_publicar(gestor.registro, config)
    if not mensajes:
        print("❌ No hay mensajes disponibles")
        return

    total = len(mensajes)
    exitosos = 0
    publicador = PublicadorFacebook(config)
    publicador.iniciar_navegador()

    try:
        for i, mensaje in enumerate(mensajes, 1):
            nombre_archivo = mensaje['nombre']
            marca = " 📌" if mensaje['elegido'] else ""
            print(f"\n{N}{C}📖 MENSAJE {i}/{total}: {nombre_archivo}{marca}{X}")

            inicio = time.time()
            exito = publicar_con_reintentos(publicador, mensaje['contenido'], 'biblico', config, gestor, nombre_archivo)
            if exito:
                exitosos += 1
                gestor.registrar_publicacion_exitosa(nombre_archivo, '', 0, 1, round(time.time() - inicio, 2), tipo='biblico')
                if mensaje['elegido']:
                    quitar_mensaje_elegido(nombre_archivo)
                print(f"{V}✅ Mensaje {i}/{total} publicado{X}")
            else:
                print(f"{R}❌ No se pudo publicar {nombre_archivo}{X}")
                gestor.registrar_error(nombre_archivo, "Falló después de todos los intentos", tipo='biblico')

            if i < total:
                print(f"\n⏳ Esperando {tiempo_minimo}s antes del siguiente mensaje...")
                time.sleep(tiempo_minimo)
    finally:
        publicador.cerrar_navegador()

    color = V if exitosos == total else (A if exitosos else R)
    print(f"\n{color}{N}" + "="*70 + X)
    print(f"{color}{N}📊 MENSAJES BÍBLICOS PUBLICADOS: {exitosos}/{total}{X}")
    print(f"{color}{N}" + "="*70 + X)


def _publicar_predicacion(config):
    gestor = GestorRegistro()
    gestor.mostrar_estadisticas()
    print(f"\n{N}{C}" + "="*70 + X)
    print(f"{N}{C}" + " " * 15 + "📤 PUBLICADOR DE PRÉDICAS EXTRAÍDAS" + X)
    print(f"{N}{C}" + " " * 20 + "Facebook - Cola de predicaciones" + X)
    print(f"{N}{C}" + "="*70 + X + "\n")

    ruta_archivo, titulo = obtener_siguiente_predicacion()
    if not ruta_archivo:
        print(f"{A}❌ No hay predicaciones pendientes{X}")
        return

    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read().strip()
        if not contenido:
            print("❌ El archivo de predicación está vacío")
            return
    except Exception as e:
        print(f"❌ Error leyendo predicación: {e}")
        return

    if config.get('agregar_introduccion_predica', True):
        intro = config.get('texto_introduccion_predica', '🎬 Predicación recomendada:\n\n')
        if intro:
            intro = intro.rstrip() + '\n\n'
            contenido = f"{intro}{contenido}"

    print(f"\n📹 Publicando predicación: {titulo}")
    publicador = PublicadorFacebook(config)
    publicador.iniciar_navegador()

    try:
        exito = publicar_con_reintentos(publicador, contenido, 'predicacion', config, gestor, titulo)
        if exito:
            gestor.registrar_publicacion_exitosa(titulo, '', 0, 1, 0, tipo='predicacion')
            try:
                from registro_historial import RegistroHistorialPredicaciones
                reg = RegistroHistorialPredicaciones()
                reg.registrar_publicacion(titulo)
            except Exception as _e:
                print(f"   ⚠️  No se pudo registrar en historial: {_e}")
            mover_predicacion_a_publicados(titulo)
            print(f"\n{V}{N}" + "="*70 + X)
            print(f"{V}{N}✅ PREDICACIÓN PUBLICADA EXITOSAMENTE{X}")
            print(f"{V}{N}" + "="*70 + X)
        else:
            print(f"\n{R}{N}" + "="*70 + X)
            print(f"{R}{N}❌ NO SE PUDO PUBLICAR LA PREDICACIÓN{X}")
            print(f"{R}{N}" + "="*70 + X)
            gestor.registrar_error(titulo, "Falló después de todos los intentos", tipo='predicacion')
    finally:
        publicador.cerrar_navegador()


def _ejecutar_secuencia_full(config):
    import subprocess
    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

    cfg = configparser.RawConfigParser(delimiters=('=',))
    cfg.read(os.path.join(base_dir, "config_global.txt"), encoding='utf-8')
    modulos = cfg.get('SECUENCIA', 'modulos_activos', fallback='biblico,extraer,publicar_predica').strip()
    lista = [m.strip() for m in modulos.split(',') if m.strip()]

    _ejecutar_modulos(config, lista)


def _base_dir_app():
    return os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))


def _comando_modulo(nombre_exe, script_relativo):
    """Ruta del .exe compilado o, en desarrollo, el script .py equivalente"""
    base_dir = _base_dir_app()
    exe = os.path.join(base_dir, nombre_exe)
    if os.path.exists(exe):
        return [exe]
    script = os.path.join(base_dir, script_relativo)
    if not getattr(sys, 'frozen', False) and os.path.exists(script):
        return [sys.executable, script]
    return None


def _ejecutar_modulos(config, lista, destinatarios=None, id_de_tarea=None):
    """Ejecuta las acciones en orden. Con id_de_tarea valida cada una antes y nunca se queda esperando respuesta"""
    import subprocess
    import json

    nombres = dict(MODULOS_DISPONIBLES)

    for modulo in lista:
        if id_de_tarea and not _validar_modulo_tarea(config, modulo, destinatarios, id_de_tarea):
            continue

        if modulo == 'biblico':
            _publicar_mensaje_biblico(config)

        elif modulo == 'extraer':
            comando = _comando_modulo('ExtractorPredicaciones.exe', os.path.join('extractores', 'extractor_whatsapp_predicaciones.py'))
            if comando:
                print("\n🎬 Iniciando extracción de predicaciones...")
                subprocess.Popen(comando).wait()
            else:
                print("⚠️  ExtractorPredicaciones.exe no encontrado")

        elif modulo == 'publicar_predica':
            if contar_predicaciones_pendientes() > 0:
                _publicar_predicacion(config)
            else:
                print("\n📭 Sin predicaciones pendientes para publicar")

        elif modulo == 'oraciones':
            comando = _comando_modulo('OracionesWhatsApp.exe', os.path.join('publicadores', 'whatsapp_oracion.py'))
            if comando:
                if destinatarios:
                    ruta = os.path.join(_base_dir_app(), 'destinatarios_ejecucion.json')
                    with open(ruta, 'w', encoding='utf-8') as f:
                        json.dump({'grupos': destinatarios}, f, ensure_ascii=False, indent=2)
                    comando = comando + ['--destinatarios', ruta]
                print("\n📱 Iniciando envío de oraciones...")
                subprocess.Popen(comando).wait()
            else:
                print("⚠️  OracionesWhatsApp.exe no encontrado")

        if id_de_tarea:
            registrar_evento_tarea(id_de_tarea, f"✅ Ejecutada \"{nombres.get(modulo, modulo).split('  ')[-1]}\"")


def _hay_destinatarios_por_defecto():
    import json
    ruta = os.path.join(_base_dir_app(), 'llamados-oracion', 'grupos.json')
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            grupos = json.load(f).get('grupos', [])
        return any(g.get('seleccionado', True) and g.get('activo', True) for g in grupos)
    except Exception:
        return False


def _abrir_configurador_sin_esperar(pestana):
    import subprocess
    base_dir = _base_dir_app()
    exe_cfg = os.path.join(base_dir, "ConfiguradorMensajes.exe")
    try:
        if os.path.exists(exe_cfg):
            subprocess.Popen([exe_cfg, f"--pestana={pestana}"])
        else:
            subprocess.Popen([sys.executable, os.path.join(base_dir, "configurador_gui.py"), f"--pestana={pestana}"])
    except Exception as e:
        print(f"⚠️  No se pudo abrir el Configurador: {e}")


def _validar_modulo_tarea(config, modulo, destinatarios, id_de_tarea):
    """Revisa lo que necesita una acción de una tarea; si falta algo avisa con cuenta regresiva y la omite"""
    from compartido.aviso_temporizado import AvisoTemporizado

    nombre_modulo = dict(MODULOS_DISPONIBLES).get(modulo, modulo).split('  ')[-1]
    problema = None
    pestana = None

    if modulo in ('extraer', 'publicar_predica') and not config.get('nombre_grupo_whatsapp', '').strip():
        problema = "Falta el nombre del grupo de WhatsApp de prédicas"
        pestana = 'extractor'
    elif modulo == 'oraciones' and not destinatarios and not _hay_destinatarios_por_defecto():
        problema = "No hay destinatarios de oración por defecto"
        pestana = 'oraciones'

    if not problema:
        return True

    print(f"\n{A}⚠️  {problema} → se omite \"{nombre_modulo}\"{X}")
    eleccion, respondio = AvisoTemporizado.preguntar(
        problema,
        f"La acción \"{nombre_modulo}\" de la tarea \"{id_de_tarea}\" no se puede ejecutar.\n"
        "Las demás acciones de la tarea continúan.",
        [('configurar', "Abrir Configurador"), ('omitir', "Omitir esta acción")],
        'omitir'
    )
    if eleccion == 'configurar':
        _abrir_configurador_sin_esperar(pestana)

    detalle = "respondido" if respondio else f"sin respuesta, {AvisoTemporizado.SEGUNDOS_DEFECTO} s"
    registrar_evento_tarea(id_de_tarea, f"⏭️ Omitida \"{nombre_modulo}\": {problema} ({detalle})")
    return False


def _ejecutar_tarea(config, id_de_tarea):
    """Ejecuta las acciones propias de una tarea automática"""
    config_tarea = obtener_config_tarea(id_de_tarea)

    if not config_tarea:
        print(f"{A}⚠️  La tarea '{id_de_tarea}' no tiene configuración propia. Se usa la secuencia general.{X}")
        registrar_evento_tarea(id_de_tarea, "⚠️ Sin configuración propia: se usó la secuencia general")
        _ejecutar_secuencia_full(config)
        return

    modulos = config_tarea.get('modulos', [])
    destinatarios = config_tarea.get('destinatarios')
    nombres = dict(MODULOS_DISPONIBLES)

    print(f"\n{N}{C}🗓️  TAREA AUTOMÁTICA: {config_tarea.get('nombre', id_de_tarea)}{X}")
    for i, modulo in enumerate(modulos, 1):
        print(f"   {i}. {nombres.get(modulo, modulo)}")
    if 'oraciones' in modulos:
        print(f"   📱 Destinatarios: {f'{len(destinatarios)} propios de la tarea' if destinatarios else 'los de por defecto'}")

    if not modulos:
        print(f"{A}⚠️  La tarea no tiene acciones activas{X}")
        registrar_evento_tarea(id_de_tarea, "⚠️ Sin acciones activas")
        return

    registrar_evento_tarea(id_de_tarea, "▶️ Inicio")
    _ejecutar_modulos(config, modulos, destinatarios, id_de_tarea)
    registrar_evento_tarea(id_de_tarea, "🏁 Fin")


def _validar_y_ejecutar_secuencia(config):
    import tkinter as tk
    from tkinter import messagebox
    import configparser as _cp
    import subprocess as _sp

    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

    cfg = _cp.ConfigParser()
    cfg.read(os.path.join(base_dir, "config_global.txt"), encoding='utf-8')
    modulos = cfg.get('SECUENCIA', 'modulos_activos', fallback='').strip()

    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    if not modulos:
        respuesta = messagebox.askyesno(
            "⚙️ Secuencia no configurada",
            "No has configurado la secuencia de módulos.\n\n"
            "¿Deseas ir al Configurador para definirla ahora?",
            parent=root
        )
        root.destroy()
        if respuesta:
            exe_cfg = os.path.join(base_dir, "ConfiguradorMensajes.exe")
            if os.path.exists(exe_cfg):
                _sp.Popen([exe_cfg, "--pestana=secuencia", "--ejecutar-despues"]).wait()
            else:
                _sp.Popen([sys.executable, "configurador_gui.py", "--pestana=secuencia", "--ejecutar-despues"]).wait()
        else:
            _abrir_consola()
            mostrar_banner()
            mostrar_configuracion(config)
            _ejecutar_secuencia_full(config)
        return

    lista = [m.strip() for m in modulos.split(',') if m.strip()]
    necesita_grupo = 'extraer' in lista or 'publicar_predica' in lista
    if necesita_grupo:
        grupo = cfg.get('PREDICACIONES', 'nombre_grupo_whatsapp', fallback='').strip()
        if not grupo:
            respuesta = messagebox.askyesno(
                "⚠️ Configuración incompleta",
                "La secuencia incluye 'Extraer Predicaciones' pero no has configurado\n"
                "el nombre del grupo de WhatsApp.\n\n"
                "¿Deseas ir al Configurador para completarlo ahora?",
                parent=root
            )
            root.destroy()
            if respuesta:
                exe_cfg = os.path.join(base_dir, "ConfiguradorMensajes.exe")
                if os.path.exists(exe_cfg):
                    _sp.Popen([exe_cfg, "--pestana=extractor", "--ejecutar-despues"]).wait()
                else:
                    _sp.Popen([sys.executable, "configurador_gui.py", "--pestana=extractor", "--ejecutar-despues"]).wait()
            else:
                _abrir_consola()
                mostrar_banner()
                mostrar_configuracion(config)
                _ejecutar_secuencia_full(config)
            return

    root.destroy()
    _abrir_consola()
    mostrar_banner()
    mostrar_configuracion(config)
    _ejecutar_secuencia_full(config)


def _ocultar_consola():
    try:
        _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if _hwnd:
            ctypes.windll.user32.ShowWindow(_hwnd, 0)
    except Exception:
        pass


def _abrir_consola():
    try:
        _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if _hwnd:
            ctypes.windll.user32.ShowWindow(_hwnd, 5)
    except Exception:
        pass
    try:
        ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass
    try:
        _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if _hwnd:
            _base = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            _ico = os.path.join(_base, 'iconos', 'bible.ico')
            if os.path.exists(_ico):
                _hicon = ctypes.windll.user32.LoadImageW(0, _ico, 1, 0, 0, 0x10)
                if _hicon:
                    ctypes.windll.user32.SendMessageW(_hwnd, 0x0080, 1, _hicon)
                    ctypes.windll.user32.SendMessageW(_hwnd, 0x0080, 0, _hicon)
    except Exception:
        pass


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--solo-biblico', action='store_true')
    parser.add_argument('--secuencia', action='store_true')
    parser.add_argument('--modulo', default=None)
    parser.add_argument('--tarea', default=None)
    args, _ = parser.parse_known_args()

    es_doble_clic = not args.solo_biblico and not args.secuencia and args.modulo is None and args.tarea is None

    estado_licencia = verificar_licencia_inicio()
    if not estado_licencia:
        _abrir_consola()
        print("\n⏰ Acceso bloqueado — período de prueba expirado o licencia inválida.")
        if args.tarea:
            registrar_evento_tarea(args.tarea, "⛔ No se ejecutó: licencia inválida o expirada")
        else:
            input("\nPresiona Enter para cerrar...")
        return

    try:
        config = leer_config_global()
    except Exception as e:
        _abrir_consola()
        print(f"❌ Error leyendo configuración: {e}")
        return

    es_full = estado_licencia.get('tipo') in ['FULL', 'MASTER'] or estado_licencia.get('developer_permanente')

    if not es_full:
        config['cantidad_por_ejecucion'] = 1
        if config['seleccion'] in ('elegidos', 'hibrido'):
            config['seleccion'] = 'aleatorio'

    if es_doble_clic and es_full:
        _validar_y_ejecutar_secuencia(config)
        return

    _abrir_consola()
    mostrar_banner()
    mostrar_configuracion(config)

    try:
        if args.tarea and es_full:
            _ejecutar_tarea(config, args.tarea)
        elif args.tarea:
            _publicar_mensaje_biblico(config)
        elif args.modulo == 'publicar_predicaciones':
            _publicar_predicacion(config)
        elif args.solo_biblico:
            _publicar_mensaje_biblico(config)
        elif args.secuencia:
            _ejecutar_secuencia_full(config)
        else:
            _publicar_mensaje_biblico(config)
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso cancelado por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n{N}👋 Finalizando programa...{X}")
        time.sleep(2)


def _verificar_wizard_completado():
    try:
        import subprocess
        import json
        config_path = os.path.join(
            os.path.expanduser("~"), ".config", "AutomaPro", "MensajesBiblicos", "config.json"
        )
        # Verificar si existe el archivo y tiene código de licencia
        tiene_configuracion = False
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    if datos.get('codigo_licencia'):
                        tiene_configuracion = True
            except Exception:
                pass

        if not tiene_configuracion:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
                wizard = os.path.join(base_dir, "WizardMensajes.exe")
            else:
                wizard = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wizard_primera_vez.py")
            if os.path.exists(wizard):
                subprocess.Popen([wizard])
            return False
        return True
    except Exception:
        return True


if __name__ == "__main__":
    # Registrar AppUserModelID para icono correcto en barra de tareas
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('AutomaPro.MensajesBiblicos')
    except Exception:
        pass

    _ocultar_consola()

    if not _verificar_wizard_completado():
        sys.exit(0)

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Proceso cancelado por el usuario\n")
        sys.exit(0)
    except Exception as e:
        import traceback
        print(f"\n❌ Error inesperado: {e}")
        traceback.print_exc()