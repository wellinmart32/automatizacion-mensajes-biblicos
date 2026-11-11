# Archivo: publicador_correo.py
# Ruta: publicadores/publicador_correo.py
# Uso: from publicadores.publicador_correo import enviar_mensajes_por_correo
# Envía mensajes por correo con SMTP (Gmail, Outlook, Yahoo u otro), un correo por destinatario
import os
import sys
import ssl
import json
import time
import smtplib
import configparser
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr

from compartido.credenciales_windows import guardar_credencial, leer_credencial

DESTINO_CREDENCIAL = "AutomaPro_MensajesBiblicos_Correo"

# servidor, puerto, seguridad
PROVEEDORES = {
    'gmail':   ("Gmail",   "smtp.gmail.com",        465, 'ssl'),
    'outlook': ("Outlook", "smtp-mail.outlook.com", 587, 'starttls'),
    'yahoo':   ("Yahoo",   "smtp.mail.yahoo.com",   465, 'ssl'),
    'otro':    ("Otro",    "",                      587, 'starttls'),
}

PIE_POR_DEFECTO = "Si no deseas recibir más estos mensajes, responde a este correo y te quitaré de la lista."


def _base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _carpeta_correo():
    carpeta = os.path.join(_base_dir(), 'correo')
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def leer_config_correo():
    """Sección [CORREO] de config_global.txt con valores por defecto (las instalaciones antiguas no la tienen)"""
    cfg = configparser.RawConfigParser(delimiters=('=',))
    cfg.read(os.path.join(_base_dir(), 'config_global.txt'), encoding='utf-8')

    def valor(clave, defecto):
        texto = cfg.get('CORREO', clave, fallback='').split('#')[0].strip()
        return texto if texto else defecto

    proveedor = valor('proveedor', 'gmail')
    _, servidor, puerto, seguridad = PROVEEDORES.get(proveedor, PROVEEDORES['otro'])
    try:
        puerto = int(valor('puerto', str(puerto)))
    except ValueError:
        pass
    try:
        pausa = max(1, int(valor('pausa_entre_envios_segundos', '3')))
    except ValueError:
        pausa = 3

    return {
        'proveedor': proveedor,
        'servidor': valor('servidor', servidor),
        'puerto': puerto,
        'seguridad': valor('seguridad', seguridad),
        'remitente': valor('remitente', ''),
        'nombre_remitente': valor('nombre_remitente', ''),
        'asunto': valor('asunto', '{titulo}'),
        'pie': valor('pie', PIE_POR_DEFECTO),
        'pausa_entre_envios_segundos': pausa,
        'enviar_biblicos': valor('enviar_biblicos', 'si') == 'si',
        'enviar_predicas': valor('enviar_predicas', 'si') == 'si',
    }


def guardar_contrasena(remitente, contrasena):
    return guardar_credencial(DESTINO_CREDENCIAL, remitente, contrasena)


def leer_contrasena():
    _, contrasena = leer_credencial(DESTINO_CREDENCIAL)
    return contrasena


def leer_destinatarios_correo():
    """[{email, nombre, seleccionado}] — seleccionado = recibe por defecto"""
    ruta = os.path.join(_carpeta_correo(), 'destinatarios.json')
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f).get('destinatarios', [])
    except Exception:
        return []


def guardar_destinatarios_correo(destinatarios):
    ruta = os.path.join(_carpeta_correo(), 'destinatarios.json')
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump({'destinatarios': destinatarios}, f, ensure_ascii=False, indent=2)


def destinatarios_correo_por_defecto():
    return [d['email'] for d in leer_destinatarios_correo() if d.get('seleccionado', True)]


def falta_configuracion_correo(destinatarios=None):
    """Texto del primer problema que impide enviar, o None si está todo listo"""
    config = leer_config_correo()
    if not config['remitente'] or not config['servidor']:
        return "Falta configurar la cuenta de correo que envía"
    if not leer_contrasena():
        return "Falta la contraseña de aplicación del correo"
    if not (destinatarios or destinatarios_correo_por_defecto()):
        return "No hay destinatarios de correo"
    return None


def _leer_registro():
    ruta = os.path.join(_carpeta_correo(), 'registro_envios.json')
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'envios': []}


def _registrar_envio(nombre_archivo, enviados, fallidos, url=None):
    registro = _leer_registro()
    if url and enviados:
        registro.setdefault('urls_predicas', []).append(url)
        registro['urls_predicas'] = registro['urls_predicas'][-1000:]
    registro['envios'].append({
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'mensaje_archivo': nombre_archivo,
        'enviados': enviados,
        'fallidos': fallidos,
    })
    registro['envios'] = registro['envios'][-500:]
    with open(os.path.join(_carpeta_correo(), 'registro_envios.json'), 'w', encoding='utf-8') as f:
        json.dump(registro, f, ensure_ascii=False, indent=2)


def registro_para_rotacion():
    """Historial de correos con la forma que usa la rotación de mensajes, para que el correo lleve su propio turno"""
    envios = [e['mensaje_archivo'] for e in _leer_registro().get('envios', []) if e.get('enviados')]
    return {
        'historial_completo': [{'tipo': 'biblico', 'mensaje_archivo': m} for m in envios],
        'historial_reciente': envios[-20:],
    }


def siguiente_predica_para_correo(texto_introduccion):
    """
    Primera prédica pendiente que aún no se envió por correo, con la misma introducción que en Facebook.
    No la mueve de la cola: sigue pendiente para Facebook.
    """
    carpeta = os.path.join(_base_dir(), 'cola-facebook', 'pendientes')
    if not os.path.exists(carpeta):
        return None
    enviadas = set(_leer_registro().get('urls_predicas', []))
    for archivo in sorted(f for f in os.listdir(carpeta) if f.endswith('.txt') and f.startswith('predica-')):
        try:
            with open(os.path.join(carpeta, archivo), 'r', encoding='utf-8') as f:
                url = f.read().strip()
        except Exception:
            continue
        if url and url not in enviadas:
            intro = texto_introduccion.rstrip() + '\n\n' if texto_introduccion else ''
            return {'nombre': archivo, 'contenido': f"{intro}{url}", 'url': url}
    return None


def _conectar(config, contrasena):
    contexto = ssl.create_default_context()
    if config['seguridad'] == 'ssl':
        servidor = smtplib.SMTP_SSL(config['servidor'], config['puerto'], context=contexto, timeout=30)
    else:
        servidor = smtplib.SMTP(config['servidor'], config['puerto'], timeout=30)
        servidor.ehlo()
        servidor.starttls(context=contexto)
        servidor.ehlo()
    servidor.login(config['remitente'], contrasena)
    return servidor


def _explicar_error(e):
    if isinstance(e, smtplib.SMTPAuthenticationError):
        return ("El correo rechazó el usuario o la contraseña. Usa una CONTRASEÑA DE APLICACIÓN "
                "(no la contraseña normal); en Gmail se crea en myaccount.google.com/apppasswords")
    if isinstance(e, (TimeoutError, OSError)) and not isinstance(e, smtplib.SMTPException):
        return f"No se pudo conectar al servidor de correo ({type(e).__name__}). Revisa servidor, puerto e internet"
    return f"{type(e).__name__}: {e}"


def probar_conexion(config, contrasena):
    """Inicia sesión y se envía un correo de prueba a sí mismo. Retorna (ok, mensaje)"""
    try:
        servidor = _conectar(config, contrasena)
        try:
            correo = EmailMessage()
            correo['From'] = formataddr((config['nombre_remitente'], config['remitente']))
            correo['To'] = config['remitente']
            correo['Subject'] = "✅ Prueba de AutomaPro — Mensajes Bíblicos"
            correo.set_content("Si recibes este correo, el envío por correo de Mensajes Bíblicos quedó configurado.")
            servidor.send_message(correo)
        finally:
            servidor.quit()
        return True, f"Conexión correcta. Se envió un correo de prueba a {config['remitente']}"
    except Exception as e:
        return False, _explicar_error(e)


def _armar_correo(config, contenido, email_destino):
    titulo = contenido.strip().split('\n')[0].strip().rstrip(':')[:120] or "Mensaje"
    correo = EmailMessage()
    correo['From'] = formataddr((config['nombre_remitente'], config['remitente']))
    correo['To'] = email_destino
    correo['Subject'] = config['asunto'].replace('{titulo}', titulo)
    cuerpo = contenido.strip()
    if config['pie']:
        cuerpo += f"\n\n—\n{config['pie']}"
    correo.set_content(cuerpo)
    return correo


def enviar_mensajes_por_correo(mensajes, emails):
    """
    mensajes: [{'nombre', 'contenido', 'url' opcional en prédicas}]; emails: lista de direcciones.
    Envía cada mensaje a cada destinatario por separado. Retorna (enviados, fallidos)
    """
    config = leer_config_correo()
    contrasena = leer_contrasena()
    total_enviados, total_fallidos = 0, 0

    print(f"📧 Desde: {config['remitente']} ({PROVEEDORES.get(config['proveedor'], ('Otro',))[0]})")
    print(f"👥 Destinatarios: {len(emails)}")

    try:
        servidor = _conectar(config, contrasena)
    except Exception as e:
        print(f"❌ {_explicar_error(e)}")
        return 0, len(mensajes) * len(emails)

    try:
        for i, mensaje in enumerate(mensajes, 1):
            print(f"\n✉️  MENSAJE {i}/{len(mensajes)}: {mensaje['nombre']}")
            enviados, fallidos = 0, 0
            for j, email in enumerate(emails, 1):
                try:
                    servidor.send_message(_armar_correo(config, mensaje['contenido'], email))
                    enviados += 1
                    print(f"   ✅ {j}/{len(emails)} {email}")
                except smtplib.SMTPServerDisconnected:
                    # Algunos servidores cortan la sesión tras varios envíos: se reconecta y se reintenta una vez
                    try:
                        servidor = _conectar(config, contrasena)
                        servidor.send_message(_armar_correo(config, mensaje['contenido'], email))
                        enviados += 1
                        print(f"   ✅ {j}/{len(emails)} {email}")
                    except Exception as e:
                        fallidos += 1
                        print(f"   ❌ {j}/{len(emails)} {email}: {_explicar_error(e)}")
                except Exception as e:
                    fallidos += 1
                    print(f"   ❌ {j}/{len(emails)} {email}: {_explicar_error(e)}")
                if j < len(emails):
                    time.sleep(config['pausa_entre_envios_segundos'])
            _registrar_envio(mensaje['nombre'], enviados, fallidos, mensaje.get('url'))
            total_enviados += enviados
            total_fallidos += fallidos
    finally:
        try:
            servidor.quit()
        except Exception:
            pass

    return total_enviados, total_fallidos
