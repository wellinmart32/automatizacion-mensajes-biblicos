import os
import sys
import time
import json
import random
import platform
import configparser

# ── Colores ANSI ──────────────────────────────────────────────
V  = '\033[92m'   # verde
R  = '\033[91m'   # rojo
A  = '\033[93m'   # amarillo
C  = '\033[96m'   # cian
N  = '\033[1m'    # negrita
X  = '\033[0m'    # reset
# ─────────────────────────────────────────────────────────────
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class PublicadorWhatsAppOracion:
    """Envía llamados de oración a grupos/chats de WhatsApp"""

    def __init__(self):
        self.driver = None

        # Determinar carpeta base según si es .exe compilado o script
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            # Si está en subcarpeta publicadores, subir un nivel
            if os.path.basename(self.base_dir) == 'publicadores':
                self.base_dir = os.path.dirname(self.base_dir)

        self.carpeta_oracion = os.path.join(self.base_dir, "llamados-oracion")
        self.archivo_mensajes = os.path.join(self.carpeta_oracion, "mensajes_oracion.txt")
        self.archivo_grupos = os.path.join(self.carpeta_oracion, "grupos.json")
        self.archivo_config = os.path.join(self.base_dir, "config_global.txt")
        self.archivo_destinatarios = None

        # Tiempos de espera
        self.ESPERA_ENTRE_GRUPOS = 3
        self.ESPERA_MAX_CARGA_WHATSAPP = 300  # Timeout máximo absoluto (dinámico)
        self.ESPERA_BUSQUEDA = 5

        self.mensajes_grupos = []
        self.mensajes_individuales = []

        # Cargar navegador desde config del módulo oraciones
        self.navegador = self._leer_navegador_config()

    def _leer_navegador_config(self):
        """Lee el navegador configurado para el módulo de oraciones"""
        try:
            config = configparser.ConfigParser()
            if os.path.exists(self.archivo_config):
                config.read(self.archivo_config, encoding='utf-8')
                # Primero busca config específica de oraciones
                if config.has_option('ORACIONES', 'navegador'):
                    nav = config['ORACIONES']['navegador'].split('#')[0].strip()
                    if nav in ['firefox', 'chrome', 'edge']:
                        return nav
                # Fallback a navegador general
                if config.has_option('GENERAL', 'navegador'):
                    nav = config['GENERAL']['navegador'].split('#')[0].strip()
                    if nav in ['firefox', 'chrome', 'edge']:
                        return nav
        except Exception as e:
            print(f"   ⚠️  Error leyendo config navegador: {e}")
        return 'firefox'  # Default
    
    def _leer_usar_perfil_config(self):
        """Lee si debe usar perfil existente desde config_global.txt"""
        try:
            config = configparser.ConfigParser()
            if os.path.exists(self.archivo_config):
                config.read(self.archivo_config, encoding='utf-8')
                if config.has_option('NAVEGADOR', 'usar_perfil_existente'):
                    val = config['NAVEGADOR']['usar_perfil_existente'].split('#')[0].strip().lower()
                    return val == 'si'
        except Exception as e:
            print(f"   ⚠️  Error leyendo config perfil: {e}")
        return True

    def cargar_mensajes(self):
        """Carga mensajes desde archivo separados por tipo"""
        if not os.path.exists(self.archivo_mensajes):
            raise Exception(f"No se encontró {self.archivo_mensajes}")

        with open(self.archivo_mensajes, 'r', encoding='utf-8') as f:
            contenido = f.read()

        if '[GRUPOS]' in contenido and '[INDIVIDUALES]' in contenido:
            partes = contenido.split('[INDIVIDUALES]')
            seccion_grupos = partes[0].replace('[GRUPOS]', '').strip()
            seccion_individuales = partes[1].strip()
            self.mensajes_grupos = [l.strip() for l in seccion_grupos.split('\n') if l.strip()]
            self.mensajes_individuales = [l.strip() for l in seccion_individuales.split('\n') if l.strip()]
        elif '[GRUPOS]' in contenido:
            seccion_grupos = contenido.replace('[GRUPOS]', '').strip()
            self.mensajes_grupos = [l.strip() for l in seccion_grupos.split('\n') if l.strip()]
            self.mensajes_individuales = self.mensajes_grupos
        else:
            self.mensajes_grupos = [l.strip() for l in contenido.split('\n') if l.strip()]
            self.mensajes_individuales = self.mensajes_grupos

        if not self.mensajes_grupos:
            raise Exception("No hay mensajes configurados en el archivo de oraciones")

        return True

    def cargar_grupos(self):
        """Carga los chats destino: los elegidos para esta ejecución o, si no hay, los seleccionados por defecto"""
        if self.archivo_destinatarios:
            if not os.path.exists(self.archivo_destinatarios):
                raise Exception(f"No se encontró el archivo de destinatarios: {self.archivo_destinatarios}")

            with open(self.archivo_destinatarios, 'r', encoding='utf-8') as f:
                datos = json.load(f)

            chats = [g for g in datos.get('grupos', []) if g.get('activo', True)]

            if not chats:
                raise Exception("La selección de destinatarios para esta ejecución está vacía.")

            print(f"🎯 Usando destinatarios elegidos para esta ejecución ({len(chats)})")
            return chats

        if not os.path.exists(self.archivo_grupos):
            raise Exception(f"No se encontró {self.archivo_grupos}")

        with open(self.archivo_grupos, 'r', encoding='utf-8') as f:
            datos = json.load(f)

        chats = [g for g in datos.get('grupos', []) if g.get('seleccionado', True) and g.get('activo', True)]

        if not chats:
            raise Exception("No hay destinatarios seleccionados. Configura en Configurador → Oraciones → Seleccionar destinatarios por defecto.")

        return chats

    def seleccionar_mensaje(self, chat):
        """Selecciona mensaje para el chat — usa asignado si existe, aleatorio si no"""
        mensaje_asignado = chat.get('mensaje_asignado', None)
        if mensaje_asignado and mensaje_asignado.strip():
            return mensaje_asignado.strip()

        tipo_chat = chat.get('tipo', 'grupo')
        if tipo_chat == "grupo":
            return random.choice(self.mensajes_grupos)
        elif tipo_chat in ["individual", "contacto"]:
            return random.choice(self.mensajes_individuales)
        else:
            return random.choice(self.mensajes_grupos)

    def iniciar_navegador(self):
        """Inicia el navegador configurado según config_global.txt"""
        print(f"\n🌐 Iniciando {self.navegador.capitalize()} para WhatsApp Web...")

        try:
            usar_perfil = self._leer_usar_perfil_config()

            if self.navegador in ('chrome', 'edge'):
                if self.navegador == 'edge':
                    # Microsoft cerró el servidor antiguo de msedgedriver; versiones viejas de Selenium Manager lo seguían usando
                    os.environ.setdefault("SE_DRIVER_MIRROR_URL", "https://msedgedriver.microsoft.com")
                    from selenium.webdriver.edge.options import Options as EdgeOptions
                    opciones = EdgeOptions()
                    clase_driver, nombre = webdriver.Edge, 'Edge'
                else:
                    opciones = ChromeOptions()
                    clase_driver, nombre = webdriver.Chrome, 'Chrome'
                opciones.add_argument("--disable-blink-features=AutomationControlled")
                # enable-logging y log-level evitan que el navegador llene la consola con mensajes internos
                opciones.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                opciones.add_argument("--log-level=3")

                perfil_dedicado = os.path.join(self.base_dir, "perfiles", f"whatsapp_{self.navegador}_compartido")
                os.makedirs(perfil_dedicado, exist_ok=True)
                opciones.add_argument(f"--user-data-dir={perfil_dedicado}")
                print(f"   ✓ Usando perfil {nombre} dedicado: {perfil_dedicado}")

                self.driver = clase_driver(options=opciones)
            else:
                import subprocess as _sp
                try:
                    _r = _sp.run(['tasklist', '/FI', 'IMAGENAME eq firefox.exe', '/NH'], capture_output=True, text=True)
                    firefox_ya_abierto = 'firefox.exe' in _r.stdout.lower()
                except Exception:
                    firefox_ya_abierto = False

                perfil_fallback = os.path.join(self.base_dir, "perfiles", "whatsapp_firefox")
                os.makedirs(perfil_fallback, exist_ok=True)

                if firefox_ya_abierto:
                    print(f"   ℹ️  Firefox ya está abierto, usando perfil dedicado...")
                    opciones = FirefoxOptions()
                    opciones.add_argument('-profile')
                    opciones.add_argument(perfil_fallback)
                    print(f"   ✓ Usando perfil dedicado: {perfil_fallback}")
                    self.driver = webdriver.Firefox(options=opciones)
                else:
                    if platform.system() == "Windows":
                        ruta_perfiles = os.path.expanduser("~/AppData/Roaming/Mozilla/Firefox/Profiles")
                    else:
                        ruta_perfiles = os.path.expanduser("~/.mozilla/firefox")

                    perfil_path = None
                    if os.path.exists(ruta_perfiles):
                        for carpeta in os.listdir(ruta_perfiles):
                            if 'default-release' in carpeta:
                                perfil_path = os.path.join(ruta_perfiles, carpeta)
                                print(f"   ✓ Usando perfil Firefox: {carpeta}")
                                break

                    opciones = FirefoxOptions()
                    if perfil_path:
                        opciones.add_argument('-profile')
                        opciones.add_argument(perfil_path)
                        try:
                            self.driver = webdriver.Firefox(options=opciones)
                        except Exception as e:
                            print(f"   ⚠️  Perfil principal bloqueado ({e}), usando perfil dedicado...")
                            opciones = FirefoxOptions()
                            opciones.add_argument('-profile')
                            opciones.add_argument(perfil_fallback)
                            self.driver = webdriver.Firefox(options=opciones)
                    else:
                        print("   ⚠️  No se encontró perfil default-release, usando perfil dedicado...")
                        opciones.add_argument('-profile')
                        opciones.add_argument(perfil_fallback)
                        self.driver = webdriver.Firefox(options=opciones)

            self.driver.maximize_window()
            print("   ✅ Navegador iniciado")
            return True

        except Exception as e:
            print(f"   ❌ Error iniciando navegador: {e}")
            return False

    @staticmethod
    def _notificar_login(titulo, mensaje):
        import threading
        def _mostrar():
            import tkinter as tk
            from compartido.toast import Toast
            root = tk.Tk()
            root.withdraw()
            Toast.advertencia(root, f"{titulo}\n{mensaje}", duracion=8000)
            root.after(8500, root.destroy)
            root.mainloop()
        threading.Thread(target=_mostrar, daemon=True).start()

    def abrir_whatsapp_web(self):
        """Abre WhatsApp Web con espera dinámica basada en progreso de carga"""
        print("\n📱 Abriendo WhatsApp Web...")

        TIMEOUT_MAXIMO        = 300  # 5 minutos máximo total
        TIMEOUT_SIN_PROGRESO  = 60   # 60s sin cambio en porcentaje → cancelar

        try:
            self.driver.get("https://web.whatsapp.com")

            print("   ⏳ Esperando que WhatsApp cargue...")
            print("   ℹ️  Si lleva mucho tiempo sin sesión, puede tardar varios minutos...")

            inicio               = time.time()
            ultimo_porcentaje    = -1
            tiempo_ultimo_cambio = time.time()
            notificado           = False

            while True:
                tiempo_total = time.time() - inicio

                # Timeout máximo absoluto
                if tiempo_total > TIMEOUT_MAXIMO:
                    print(f"\n   ❌ WhatsApp no cargó en {TIMEOUT_MAXIMO // 60} minutos")
                    print("   💡 Verifica que tu móvil esté conectado y sincronizado")
                    return False

                # Verificar si ya cargó la interfaz principal
                if self._encontrar_barra_busqueda(timeout=3):
                    print(f"\n   ✅ WhatsApp Web cargado correctamente")
                    time.sleep(2)
                    return True

                # Detectar porcentaje de carga para seguimiento de progreso
                porcentaje_actual = -1
                try:
                    import re
                    elementos = self.driver.find_elements(
                        By.XPATH, "//*[contains(text(), '%')]"
                    )
                    for el in elementos:
                        texto = el.text
                        if '%' in texto and any(c.isdigit() for c in texto):
                            numeros = re.findall(r'\d+', texto)
                            if numeros:
                                porcentaje_actual = int(numeros[0])
                                break
                except Exception:
                    pass

                # Verificar si hay progreso
                if porcentaje_actual != -1:
                    if porcentaje_actual != ultimo_porcentaje:
                        ultimo_porcentaje    = porcentaje_actual
                        tiempo_ultimo_cambio = time.time()
                        print(f"   ⏳ Cargando... {porcentaje_actual}% "
                              f"({int(tiempo_total)}s transcurridos)    ", end='\r')
                    else:
                        sin_progreso = time.time() - tiempo_ultimo_cambio
                        if sin_progreso > TIMEOUT_SIN_PROGRESO:
                            print(f"\n   ❌ Sin progreso por {TIMEOUT_SIN_PROGRESO}s "
                                  f"(detenido en {ultimo_porcentaje}%)")
                            print("   💡 Verifica tu conexión a internet y que el móvil esté activo")
                            return False
                        print(f"   ⏳ Cargando... {porcentaje_actual}% "
                              f"(sin cambio por {int(sin_progreso)}s)    ", end='\r')
                else:
                    sin_progreso = time.time() - tiempo_ultimo_cambio
                    print(f"   ⏳ Esperando interfaz... {int(tiempo_total)}s    ", end='\r')

                    if not notificado:
                        try:
                            qr_elements = self.driver.find_elements(
                                By.XPATH, "//canvas[@aria-label]"
                            )
                            if qr_elements:
                                self._notificar_login(
                                    "Escanea el código QR",
                                    "Abre WhatsApp → Dispositivos vinculados\nVincular dispositivo."
                                )
                                notificado = True
                        except Exception:
                            pass

                    if sin_progreso > TIMEOUT_SIN_PROGRESO and tiempo_total > 30:
                        print(f"\n   ❌ Sin actividad por {TIMEOUT_SIN_PROGRESO}s")
                        print("   💡 Verifica tu conexión a internet")
                        return False

                time.sleep(3)

        except Exception as e:
            print(f"   ❌ Error abriendo WhatsApp Web: {e}")
            return False

    # Selectores en cascada: WhatsApp cambia su HTML de vez en cuando.
    SELECTORES_BARRA_BUSQUEDA = [
        "//input[@data-tab='3']",
        "//div[@contenteditable='true'][@data-tab='3']",
        "//input[contains(@aria-label, 'Buscar')]",
    ]

    SELECTORES_CAMPO_MENSAJE = [
        "//div[@contenteditable='true'][@data-tab='10']",
        "//div[@contenteditable='true'][contains(@aria-label, 'Escribe un mensaje')]",
    ]

    def _encontrar_barra_busqueda(self, timeout=3):
        """Busca la barra de búsqueda probando varios selectores"""
        for selector in self.SELECTORES_BARRA_BUSQUEDA:
            try:
                elemento = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                return elemento
            except Exception:
                continue
        return None

    def _encontrar_campo_mensaje(self, timeout=15):
        """Busca el campo de escribir mensaje probando varios selectores"""
        for selector in self.SELECTORES_CAMPO_MENSAJE:
            try:
                elemento = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                return elemento
            except Exception:
                continue
        return None

    def buscar_chat(self, nombre_chat):
        """Busca chat por nombre"""
        print(f"\n🔍 Buscando chat: {nombre_chat}")
        try:
            from selenium.webdriver.common.action_chains import ActionChains

            # Cerrar chat abierto volviendo al panel lateral
            try:
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(0.5)
            except:
                pass

            # Clic en el panel lateral para asegurar foco correcto
            try:
                panel = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[@id='pane-side']")
                    )
                )
                panel.click()
                time.sleep(0.5)
            except:
                pass

            campo_busqueda = self._encontrar_barra_busqueda(timeout=10)
            if not campo_busqueda:
                print("   ❌ No se encontró la barra de búsqueda")
                return False
            campo_busqueda.click()
            time.sleep(0.8)

            # Limpiar campo con JavaScript + disparo de evento
            self.driver.execute_script("""
                var el = arguments[0];
                el.focus();
                el.innerHTML = '';
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new InputEvent('input', {bubbles: true}));
            """, campo_busqueda)
            time.sleep(0.5)

            import pyperclip
            pyperclip.copy(nombre_chat)
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(2.5)

            try:
                contacto = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, f"//span[@title='{nombre_chat}']"))
                )
                contacto.click()
                time.sleep(2)
                print(f"   ✅ Chat '{nombre_chat}' abierto")
                return True
            except:
                try:
                    contacto_alt = WebDriverWait(self.driver, 8).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, f"//span[contains(@title, '{nombre_chat}')]")
                        )
                    )
                    contacto_alt.click()
                    time.sleep(2)
                    print(f"   ✅ Chat '{nombre_chat}' abierto")
                    return True
                except:
                    print(f"   ❌ No se encontró '{nombre_chat}'")
                    return False

        except Exception as e:
            print(f"   ❌ Error buscando chat: {e}")
            return False

    def enviar_mensaje(self, mensaje):
        """Envía mensaje en chat activo"""
        print(f"\n✉️  Enviando mensaje...")
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            time.sleep(1.5)

            campo_mensaje = self._encontrar_campo_mensaje(timeout=15)
            if not campo_mensaje:
                print("   ❌ No se encontró el campo de mensaje")
                return False

            self.driver.execute_script("arguments[0].focus();", campo_mensaje)
            time.sleep(0.5)
            campo_mensaje.click()
            time.sleep(0.5)

            import pyperclip
            pyperclip.copy(mensaje)
            time.sleep(0.3)
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(1.0)

            contenido = self.driver.execute_script(
                "return arguments[0].innerText || '';", campo_mensaje)
            if not contenido.strip():
                print("   ⚠️  Campo vacío, reintentando...")
                campo_mensaje.click()
                time.sleep(0.5)
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                time.sleep(1.0)

            ActionChains(self.driver).send_keys(Keys.ENTER).perform()
            time.sleep(2)

            print(f"   ✅ Mensaje enviado: {mensaje[:50]}...")
            return True

        except Exception as e:
            print(f"   ❌ Error enviando mensaje: {e}")
            import traceback
            traceback.print_exc()
            return False

    def publicar_en_todos_los_chats(self):
        """Función principal - publica en todos los chats"""
        print(f"\n{N}{C}" + "="*70 + X)
        print(f"{N}{C}" + " " * 15 + "📱 PUBLICADOR DE LLAMADOS DE ORACIÓN" + X)
        print(f"{N}{C}" + " " * 20 + "WhatsApp Web - Chats" + X)
        print(f"{N}{C}" + "="*70 + X + "\n")

        print(f"🌐 Navegador configurado: {self.navegador.capitalize()}")

        try:
            self.cargar_mensajes()
            chats = self.cargar_grupos()
        except Exception as e:
            print(f"❌ Error cargando archivos: {e}")
            return False

        grupos_count = sum(1 for c in chats if c.get('tipo') == 'grupo')
        individuales_count = sum(1 for c in chats if c.get('tipo') == 'individual')

        print(f"\n📋 CONFIGURACIÓN:")
        print(f"   📝 Mensajes para grupos: {len(self.mensajes_grupos)}")
        print(f"   📝 Mensajes para individuales: {len(self.mensajes_individuales)}")
        print(f"   👥 Grupos activos: {grupos_count}")
        print(f"   👤 Individuales activos: {individuales_count}")
        print(f"   📈 Total chats: {len(chats)}")

        print(f"\n📋 CHATS A PUBLICAR:")
        for i, chat in enumerate(chats, 1):
            tipo_emoji = "👥" if chat.get('tipo') == 'grupo' else "👤"
            print(f"   {i}. {tipo_emoji} {chat['nombre']} ({chat.get('tipo', 'grupo')})")

        if not self.iniciar_navegador():
            return False

        if not self.abrir_whatsapp_web():
            self.cerrar_navegador()
            return False

        exitos = 0
        fallos = 0

        print(f"\n{N}{A}" + "="*70 + X)
        print(f"{N}{A}▶ INICIANDO PUBLICACIONES{X}")
        print(f"{N}{A}" + "="*70 + X)

        for i, chat in enumerate(chats, 1):
            nombre_chat = chat['nombre']
            tipo_chat = chat.get('tipo', 'grupo')
            tipo_emoji = "👥" if tipo_chat == 'grupo' else "👤"

            print(f"\n{'='*70}")
            print(f"📨 CHAT {i}/{len(chats)}: {tipo_emoji} {nombre_chat} ({tipo_chat})")
            print(f"{'='*70}")

            mensaje = self.seleccionar_mensaje(chat)
            print(f"🎲 Mensaje seleccionado: '{mensaje}'")

            if not self.buscar_chat(nombre_chat):
                print(f"   ⚠️  Saltando chat '{nombre_chat}'")
                fallos += 1
                continue

            if self.enviar_mensaje(mensaje):
                exitos += 1
                print(f"   ✅ Publicación exitosa en '{nombre_chat}'")
            else:
                fallos += 1
                print(f"   ❌ Fallo en '{nombre_chat}'")

            if i < len(chats):
                print(f"\n   ⏳ Esperando {self.ESPERA_ENTRE_GRUPOS}s antes del siguiente chat...")
                time.sleep(self.ESPERA_ENTRE_GRUPOS)

        print(f"\n{N}" + "="*70 + X)
        print(f"{N}📈 RESUMEN DE PUBLICACIONES{X}")
        print(f"{N}" + "="*70 + X)
        print(f"   {V}✅ Exitosas: {exitos}{X}")
        print(f"   {R}❌ Fallidas: {fallos}{X}")
        print(f"   📈 Total chats: {len(chats)}")
        if len(chats) > 0:
            color_tasa = V if exitos == len(chats) else A
            print(f"   {color_tasa}🎯 Tasa de éxito: {(exitos/len(chats)*100):.1f}%{X}")
        print(f"{N}" + "="*70 + X)

        self.cerrar_navegador()
        return exitos > 0

    def cerrar_navegador(self):
        """Cierra navegador"""
        if self.driver:
            print("\n🔒 Cerrando navegador...")
            try:
                self.driver.quit()
                print("   ✅ Navegador cerrado")
            except:
                pass


def main():
    """Función principal"""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('AutomaPro.OracionesWhatsApp')
    except Exception:
        pass

    # Habilitar colores ANSI en consola Windows
    try:
        import ctypes as _ct
        _ct.windll.kernel32.SetConsoleMode(_ct.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

    # Ícono personalizado en ventana de consola
    try:
        import ctypes as _ct
        _hwnd = 0
        for _ in range(50):
            _hwnd = _ct.windll.kernel32.GetConsoleWindow()
            if _hwnd:
                break
            time.sleep(0.1)
        if _hwnd:
            _base = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            _ico = os.path.join(_base, 'iconos', 'pray.ico')
            if os.path.exists(_ico):
                _hicon = _ct.windll.user32.LoadImageW(0, _ico, 1, 0, 0, 0x10)
                if _hicon:
                    _ct.windll.user32.SendMessageW(_hwnd, 0x0080, 1, _hicon)
                    _ct.windll.user32.SendMessageW(_hwnd, 0x0080, 0, _hicon)
                    # Reaplicar después de un momento para garantizar
                    time.sleep(0.3)
                    _ct.windll.user32.SendMessageW(_hwnd, 0x0080, 1, _hicon)
                    _ct.windll.user32.SendMessageW(_hwnd, 0x0080, 0, _hicon)
    except Exception:
        pass

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--destinatarios', default=None)
    args, _ = parser.parse_known_args()

    publicador = PublicadorWhatsAppOracion()
    if args.destinatarios:
        publicador.archivo_destinatarios = os.path.abspath(args.destinatarios)

    try:
        exito = publicador.publicar_en_todos_los_chats()

        if exito:
            print(f"\n{V}{N}✅ Proceso completado exitosamente{X}")
        else:
            print(f"\n{A}{N}⚠️  Proceso completado con errores{X}")

    except KeyboardInterrupt:
        print("\n\n❌ Proceso cancelado por el usuario")
        publicador.cerrar_navegador()

    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        publicador.cerrar_navegador()

    finally:
        print("\n👋 Finalizando programa...")
        time.sleep(2)


if __name__ == "__main__":
    main()