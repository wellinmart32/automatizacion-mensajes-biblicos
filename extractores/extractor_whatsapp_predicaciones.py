import os
import sys
import time
import json
import platform
import configparser
import requests

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


class ExtractorWhatsAppPredicaciones:
    """
    Extractor de predicaciones desde WhatsApp Web - VERSIÓN FINAL
    - Extrae de más nuevo a más viejo con scroll inteligente
    - Detecta predicaciones ya publicadas (historial JSON)
    - Se detiene al tener 5 pendientes o al llegar al inicio del grupo
    """
    
    def __init__(self):
        import sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.driver = None
        self.base_dir = base_dir
        self.archivo_config = os.path.join(base_dir, "config_global.txt")
        self.carpeta_pendientes = os.path.join(base_dir, "cola-facebook", "pendientes")
        self.carpeta_publicados = os.path.join(base_dir, "cola-facebook", "publicados")
        self.archivo_historial = os.path.join(base_dir, "cola-facebook", "historial_publicados.json")

        self.PREDICACIONES_OBJETIVO = 5
        self.MAX_SCROLLS = 200
        self.SCROLLS_SIN_CAMBIO_LIMITE = 15

        os.makedirs(self.carpeta_pendientes, exist_ok=True)
        os.makedirs(self.carpeta_publicados, exist_ok=True)
    
    def cargar_historial(self):
        """Carga el historial de predicaciones publicadas"""
        if os.path.exists(self.archivo_historial):
            try:
                with open(self.archivo_historial, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self._crear_historial_vacio()
        return self._crear_historial_vacio()
    
    def _crear_historial_vacio(self):
        """Crea estructura de historial vacío"""
        return {
            "urls_publicadas": [],
            "total_publicadas": 0,
            "ultima_actualizacion": None
        }
    
    def contar_pendientes(self):
        """Cuenta cuántas predicaciones hay pendientes"""
        if not os.path.exists(self.carpeta_pendientes):
            return 0
        
        archivos = [f for f in os.listdir(self.carpeta_pendientes) 
                   if f.startswith('predica-') and f.endswith('.txt')]
        return len(archivos)
    
    def obtener_siguiente_numero(self):
        """Obtiene el siguiente número de predicación disponible"""
        todos = []
        
        for carpeta in [self.carpeta_pendientes, self.carpeta_publicados]:
            if os.path.exists(carpeta):
                for archivo in os.listdir(carpeta):
                    if archivo.startswith('predica-') and archivo.endswith('.txt'):
                        try:
                            num = int(archivo.replace('predica-', '').replace('.txt', ''))
                            todos.append(num)
                        except:
                            pass
        
        return max(todos) + 1 if todos else 1
    
    def _leer_config_navegador(self):
        """Lee navegador, perfil y maximizar desde config_global.txt"""
        try:
            config = configparser.RawConfigParser(delimiters=('=',))
            if os.path.exists(self.archivo_config):
                config.read(self.archivo_config, encoding='utf-8')
                nav = 'firefox'
                usar_perfil = True
                maximizar = True
                if config.has_option('PREDICACIONES', 'navegador'):
                    nav = config['PREDICACIONES']['navegador'].split('#')[0].strip()
                if config.has_option('PREDICACIONES', 'usar_perfil_existente'):
                    usar_perfil = config['PREDICACIONES']['usar_perfil_existente'].split('#')[0].strip().lower() == 'si'
                if config.has_option('NAVEGADOR', 'maximizar_ventana'):
                    maximizar = config['NAVEGADOR']['maximizar_ventana'].split('#')[0].strip().lower() == 'si'
                return nav, usar_perfil, maximizar
        except Exception as e:
            print(f"⚠️  Error leyendo config navegador: {e}")
        return 'firefox', True, True

    def iniciar_navegador(self):
        """Inicializa el navegador configurado en [PREDICACIONES]"""
        navegador, usar_perfil, maximizar = self._leer_config_navegador()
        print(f"🌐 Iniciando {navegador.capitalize()} para WhatsApp Web...")

        try:
            if navegador in ('chrome', 'edge'):
                import subprocess as _sp
                if navegador == 'edge':
                    # Microsoft cerró el servidor antiguo de msedgedriver; versiones viejas de Selenium Manager lo seguían usando
                    os.environ.setdefault("SE_DRIVER_MIRROR_URL", "https://msedgedriver.microsoft.com")
                    from selenium.webdriver.edge.options import Options as OpcionesNavegador
                    clase_driver, proceso, nombre = webdriver.Edge, 'msedge.exe', 'Edge'
                else:
                    from selenium.webdriver.chrome.options import Options as OpcionesNavegador
                    clase_driver, proceso, nombre = webdriver.Chrome, 'chrome.exe', 'Chrome'
                try:
                    _r = _sp.run(['tasklist', '/FI', f'IMAGENAME eq {proceso}', '/NH'], capture_output=True, text=True)
                    ya_abierto = proceso in _r.stdout.lower()
                except Exception:
                    ya_abierto = False

                if ya_abierto:
                    print(f"   ℹ️  {nombre} ya está abierto, usando instancia separada...")

                perfil_dedicado = os.path.join(self.base_dir, "perfiles", f"whatsapp_{navegador}_compartido")
                os.makedirs(perfil_dedicado, exist_ok=True)

                opciones = OpcionesNavegador()
                opciones.add_argument("--disable-blink-features=AutomationControlled")
                # enable-logging y log-level evitan que el navegador llene la consola con mensajes internos
                opciones.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                opciones.add_argument("--log-level=3")
                opciones.add_argument(f"--user-data-dir={perfil_dedicado}")
                print(f"   ✓ Usando perfil {nombre} dedicado: {perfil_dedicado}")

                try:
                    self.driver = clase_driver(options=opciones)
                except Exception as e:
                    print(f"   ⚠️  Perfil bloqueado ({e}), usando perfil temporal...")
                    import tempfile
                    perfil_tmp = tempfile.mkdtemp(prefix=f"{navegador}_wp_tmp_")
                    opciones2 = OpcionesNavegador()
                    opciones2.add_argument("--disable-blink-features=AutomationControlled")
                    opciones2.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
                    opciones2.add_argument("--log-level=3")
                    opciones2.add_argument(f"--user-data-dir={perfil_tmp}")
                    self.driver = clase_driver(options=opciones2)
            else:
                import subprocess as _sp
                try:
                    _r = _sp.run(['tasklist', '/FI', 'IMAGENAME eq firefox.exe', '/NH'], capture_output=True, text=True)
                    firefox_ya_abierto = 'firefox.exe' in _r.stdout.lower()
                except Exception:
                    firefox_ya_abierto = False

                perfil_fallback = os.path.join(self.base_dir, "perfiles", "whatsapp_firefox")
                os.makedirs(perfil_fallback, exist_ok=True)

                opciones = FirefoxOptions()
                if usar_perfil and not firefox_ya_abierto:
                    if platform.system() == "Windows":
                        ruta_perfiles = os.path.expanduser("~/AppData/Roaming/Mozilla/Firefox/Profiles")
                    else:
                        ruta_perfiles = os.path.expanduser("~/.mozilla/firefox")

                    perfil_path = None
                    lock_libre = False
                    if os.path.exists(ruta_perfiles):
                        for carpeta in os.listdir(ruta_perfiles):
                            if 'default-release' in carpeta:
                                perfil_path = os.path.join(ruta_perfiles, carpeta)
                                lock_path = os.path.join(perfil_path, 'lock')
                                lock_path2 = os.path.join(perfil_path, '.parentlock')
                                lock_libre = not os.path.exists(lock_path) and not os.path.exists(lock_path2)
                                print(f"   ✓ Perfil Firefox encontrado: {carpeta}")
                                if not lock_libre:
                                    print(f"   ⚠️  Perfil en uso, usando perfil dedicado...")
                                break

                    if perfil_path and lock_libre:
                        opciones.add_argument('-profile')
                        opciones.add_argument(perfil_path)
                        try:
                            self.driver = webdriver.Firefox(options=opciones)
                            if maximizar:
                                self.driver.maximize_window()
                            print("📱 Abriendo WhatsApp Web...")
                            self.driver.get("https://web.whatsapp.com")
                            return True
                        except Exception as e:
                            print(f"   ⚠️  Perfil principal bloqueado ({e}), usando perfil dedicado...")
                            try:
                                if self.driver:
                                    self.driver.quit()
                                    self.driver = None
                            except Exception:
                                pass
                            opciones = FirefoxOptions()
                elif firefox_ya_abierto:
                    print(f"   ℹ️  Firefox ya está abierto, usando perfil dedicado...")

                opciones.add_argument('-profile')
                opciones.add_argument(perfil_fallback)
                print(f"   ✓ Usando perfil dedicado: {perfil_fallback}")
                self.driver = webdriver.Firefox(options=opciones)

            if maximizar:
                self.driver.maximize_window()
            print("   ✅ Navegador iniciado")
            print("📱 Abriendo WhatsApp Web...")
            self.driver.get("https://web.whatsapp.com")

            return True

        except Exception as e:
            print(f"❌ Error iniciando navegador: {e}")
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

    # Selectores en cascada: WhatsApp cambia su HTML de vez en cuando.
    # Se prueban en orden hasta que uno funcione.
    SELECTORES_BARRA_BUSQUEDA = [
        "//input[@data-tab='3']",
        "//div[@contenteditable='true'][@data-tab='3']",
        "//input[contains(@aria-label, 'Buscar')]",
    ]

    # Selectores en cascada para identificar mensajes propios dentro del chat.
    # WhatsApp ya no usa la clase 'message-out'; ahora se detecta por el
    # ícono de estado de entrega (✓ Enviado / ✓✓ Leído), que solo aparece
    # en los mensajes que el usuario envió.
    SELECTORES_MENSAJES_PROPIOS = [
        "//div[@data-testid='msg-container'][.//span[contains(@aria-label, 'Enviado')]]",
        "//div[@data-testid='msg-container'][.//span[contains(@aria-label, 'Leído')]]",
        "//div[contains(@class, 'message-out')]",
    ]

    def _encontrar_mensajes_propios(self):
        """Encuentra los mensajes propios en el DOM probando varios selectores"""
        for selector in self.SELECTORES_MENSAJES_PROPIOS:
            try:
                elementos = self.driver.find_elements(By.XPATH, selector)
                if elementos:
                    return elementos
            except Exception:
                continue
        return []

    def _encontrar_barra_busqueda(self, timeout=3):
        """Busca la barra de búsqueda probando varios selectores por si WhatsApp cambió su HTML"""
        for selector in self.SELECTORES_BARRA_BUSQUEDA:
            try:
                elemento = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                return elemento
            except Exception:
                continue
        return None

    def esperar_whatsapp_cargado(self, timeout=300):
        """Espera a que WhatsApp Web esté completamente cargado"""
        print("⏳ Esperando que WhatsApp Web cargue...")
        print("   (Si no has iniciado sesión, escanea el código QR)")

        TIMEOUT_SIN_PROGRESO = 60
        import re

        notificado           = False
        inicio               = time.time()
        ultimo_porcentaje    = -1
        tiempo_ultimo_cambio = time.time()

        try:
            while True:
                tiempo_total = time.time() - inicio

                if tiempo_total > timeout:
                    print(f"\n❌ WhatsApp no cargó en {timeout // 60} minutos")
                    return False

                if self._encontrar_barra_busqueda(timeout=3):
                    print("\n✅ WhatsApp Web cargado correctamente\n")
                    return True

                porcentaje_actual = -1
                try:
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

                if porcentaje_actual != -1:
                    if porcentaje_actual != ultimo_porcentaje:
                        ultimo_porcentaje    = porcentaje_actual
                        tiempo_ultimo_cambio = time.time()
                        print(f"⏳ Cargando... {porcentaje_actual}% ({int(tiempo_total)}s)    ", end='\r')
                    else:
                        sin_progreso = time.time() - tiempo_ultimo_cambio
                        if sin_progreso > TIMEOUT_SIN_PROGRESO:
                            print(f"\n❌ Sin progreso por {TIMEOUT_SIN_PROGRESO}s (detenido en {ultimo_porcentaje}%)")
                            return False
                        print(f"⏳ Cargando... {porcentaje_actual}% (sin cambio {int(sin_progreso)}s)    ", end='\r')
                else:
                    sin_progreso = time.time() - tiempo_ultimo_cambio
                    print(f"⏳ Esperando interfaz... {int(tiempo_total)}s    ", end='\r')

                    if not notificado:
                        try:
                            qr_elements = self.driver.find_elements(By.XPATH, "//canvas[@aria-label]")
                            if qr_elements:
                                self._notificar_login(
                                    "Escanea el código QR",
                                    "Abre WhatsApp → Dispositivos vinculados\nVincular dispositivo."
                                )
                                notificado = True
                        except Exception:
                            pass

                    if sin_progreso > TIMEOUT_SIN_PROGRESO and tiempo_total > 30:
                        print(f"\n❌ Sin actividad por {TIMEOUT_SIN_PROGRESO}s")
                        return False

                time.sleep(3)

        except Exception as e:
            print(f"\n❌ Error esperando carga de WhatsApp: {e}")
            return False
    
    def buscar_grupo(self, nombre_grupo):
        """Busca y abre un grupo específico"""
        print(f"🔍 Buscando grupo: '{nombre_grupo}'")
        
        try:
            # Limpiar barra de búsqueda
            barra_busqueda = self._encontrar_barra_busqueda(timeout=10)
            if not barra_busqueda:
                print("❌ No se encontró la barra de búsqueda")
                return False
            barra_busqueda.click()
            time.sleep(0.5)
            
            barra_busqueda.send_keys(Keys.CONTROL + "a")
            barra_busqueda.send_keys(Keys.BACKSPACE)
            time.sleep(0.5)
            
            # Escribir nombre del grupo letra por letra
            for caracter in nombre_grupo:
                barra_busqueda.send_keys(caracter)
                time.sleep(0.05)
            time.sleep(3)
            
            # Hacer clic en el primer resultado
            resultado = self.driver.find_element(
                By.XPATH, f"//span[@title='{nombre_grupo}']"
            )
            resultado.click()
            time.sleep(3)
            
            print(f"✅ Grupo '{nombre_grupo}' abierto\n")
            return True
            
        except Exception as e:
            print(f"❌ Error buscando grupo: {e}")
            return False
    
    def extraer_siguiente_lote(self, cantidad=None, indice_inicio=0, solo_propios=True):
        """
        NUEVA ESTRATEGIA INTELIGENTE:
        Extrae predicaciones con scroll progresivo y detección de publicadas
        Se detiene al tener 5 pendientes o al llegar al inicio del grupo
        """
        if cantidad is None:
            cantidad = self.PREDICACIONES_OBJETIVO
        
        print(f"\n{N}{C}" + "="*70 + X)
        print(f"{N}{C}🎯 EXTRACCIÓN INTELIGENTE DE PREDICACIONES{X}")
        print(f"{N}{C}" + "="*70 + X)
        print(f"   {N}🎯 Objetivo:{X} {self.PREDICACIONES_OBJETIVO} predicaciones pendientes")
        print(f"   {N}📊 Actualmente pendientes:{X} {self.contar_pendientes()}")
        print(f"{N}{C}" + "="*70 + X + "\n")
        
        # Cargar historial de publicadas
        historial = self.cargar_historial()
        urls_publicadas = set(historial["urls_publicadas"])
        print(f"📚 Historial cargado: {len(urls_publicadas)} predicaciones ya publicadas\n")
        
        try:
            contenedor_chat = self.driver.find_element(By.ID, "main")
            
            predicaciones_extraidas = []
            numero_siguiente = self.obtener_siguiente_numero()
            scrolls_realizados = 0
            scrolls_sin_nuevos = 0
            
            print("🔄 Iniciando extracción...\n")
            
            while True:
                # Verificar si ya tenemos suficientes pendientes
                total_pendientes = self.contar_pendientes() + len(predicaciones_extraidas)
                
                if total_pendientes >= self.PREDICACIONES_OBJETIVO:
                    print(f"\n✅ OBJETIVO ALCANZADO: {total_pendientes} predicaciones pendientes")
                    break
                
                # Seguridad: límite de scrolls
                if scrolls_realizados >= self.MAX_SCROLLS:
                    print(f"\n⚠️  Límite de scrolls alcanzado ({self.MAX_SCROLLS})")
                    break
                
                # Seguridad: muchos scrolls sin encontrar nuevas
                if scrolls_sin_nuevos >= self.SCROLLS_SIN_CAMBIO_LIMITE:
                    print(f"\n⛔ {self.SCROLLS_SIN_CAMBIO_LIMITE} scrolls sin encontrar predicaciones nuevas")
                    print("   Probablemente llegamos al inicio del grupo")
                    break
                
                # Obtener mensajes actuales del DOM (solo mensajes propios)
                mensajes_dom = self._encontrar_mensajes_propios()
                
                print(f"{'─'*60}")
                print(f"📊 Iteración #{scrolls_realizados + 1}")
                print(f"{'─'*60}")
                print(f"   Mensajes en DOM: {len(mensajes_dom)}")
                print(f"   Pendientes actuales: {total_pendientes}/{self.PREDICACIONES_OBJETIVO}")
                
                # Extraer URLs de los mensajes actuales
                nuevas_extraidas = 0
                
                for mensaje in mensajes_dom:
                    url = self._extraer_predicacion_de_mensaje(mensaje)
                    
                    if not url:
                        continue
                    
                    # ¿Ya está publicada?
                    if url in urls_publicadas:
                        continue
                    
                    # ¿Ya la extrajimos en esta sesión?
                    if any(p['contenido'] == url for p in predicaciones_extraidas):
                        continue
                    
                    # ✅ Es nueva, extraer
                    predicaciones_extraidas.append({
                        'tipo': 'enlace',
                        'contenido': url,
                        'numero': numero_siguiente
                    })
                    
                    print(f"   ✅ Nueva: predica-{numero_siguiente:03d}.txt")
                    print(f"      URL: {url[:60]}...")
                    
                    numero_siguiente += 1
                    nuevas_extraidas += 1
                    
                    # Verificar si ya tenemos suficientes
                    if self.contar_pendientes() + len(predicaciones_extraidas) >= self.PREDICACIONES_OBJETIVO:
                        break
                
                if nuevas_extraidas > 0:
                    print(f"   📦 Extraídas en esta iteración: {nuevas_extraidas}")
                    scrolls_sin_nuevos = 0
                else:
                    scrolls_sin_nuevos += 1
                    print(f"   ⏭️  Sin nuevas ({scrolls_sin_nuevos}/{self.SCROLLS_SIN_CAMBIO_LIMITE})")
                
                # Si ya tenemos suficientes, parar
                if self.contar_pendientes() + len(predicaciones_extraidas) >= self.PREDICACIONES_OBJETIVO:
                    break
                
                # Hacer scroll hacia arriba para cargar mensajes más antiguos
                print(f"   🔄 Haciendo scroll para cargar mensajes más antiguos...")
                self._hacer_scroll_arriba(contenedor_chat)
                scrolls_realizados += 1
                
                # Esperar a que WhatsApp cargue mensajes
                time.sleep(5)
            
            print(f"\n{N}" + "="*70 + X)
            print(f"{N}📊 RESUMEN DE EXTRACCIÓN{X}")
            print(f"{N}" + "="*70 + X)
            print(f"   {V}Total extraídas: {len(predicaciones_extraidas)}{X}")
            print(f"   Scrolls realizados: {scrolls_realizados}")
            print(f"   Pendientes finales: {self.contar_pendientes() + len(predicaciones_extraidas)}")
            print(f"{N}" + "="*70 + X + "\n")
            
            return predicaciones_extraidas
            
        except Exception as e:
            print(f"\n❌ ERROR durante extracción: {e}")
            import traceback
            traceback.print_exc()
            return predicaciones_extraidas
    
    def _hacer_scroll_arriba(self, contenedor_chat):
        """Hace scroll hacia arriba usando múltiples estrategias"""
        try:
            # Estrategia 1: scrollTop
            current_scroll = self.driver.execute_script(
                "return arguments[0].scrollTop;", 
                contenedor_chat
            )
            new_position = max(0, current_scroll - 3000)
            self.driver.execute_script(
                f"arguments[0].scrollTop = {new_position};", 
                contenedor_chat
            )
            time.sleep(0.5)
            
            # Estrategia 2: scrollIntoView del primer mensaje
            try:
                primer_mensaje = self.driver.find_element(
                    By.XPATH, 
                    "(//div[contains(@class, 'message-out')])[1]"
                )
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'start', behavior: 'smooth'});", 
                    primer_mensaje
                )
                time.sleep(0.5)
            except:
                pass
                
        except Exception as e:
            print(f"   ⚠️  Error en scroll: {e}")
    
    def _extraer_predicacion_de_mensaje(self, elemento_mensaje):
        """
        Extrae el contenido (URL) de un mensaje individual
        Retorna la URL o None si no encuentra nada válido
        """
        try:
            # Estrategia 1: Buscar enlaces con clase copyable-text
            try:
                enlaces_copyable = elemento_mensaje.find_elements(
                    By.XPATH, ".//a[contains(@class, 'copyable-text')]"
                )
                
                for enlace in enlaces_copyable:
                    href = enlace.get_attribute('href')
                    if href and self._es_url_valida(href):
                        return href
            except:
                pass
            
            # Estrategia 2: Buscar en texto con regex
            try:
                texto_elemento = elemento_mensaje.find_element(
                    By.XPATH, ".//span[contains(@class, 'copyable-text')]"
                )
                texto = texto_elemento.text
                
                import re
                patron_url = r'https?://(?:www\.)?(?:instagram\.com|youtube\.com|youtu\.be|facebook\.com|fb\.watch|tiktok\.com)[^\s]+'
                match = re.search(patron_url, texto)
                
                if match:
                    return match.group(0)
            except:
                pass
            
            # Estrategia 3: Método tradicional
            try:
                enlaces = elemento_mensaje.find_elements(
                    By.XPATH, ".//a[contains(@href, 'youtube.com') or "
                             "contains(@href, 'youtu.be') or "
                             "contains(@href, 'instagram.com') or "
                             "contains(@href, 'facebook.com') or "
                             "contains(@href, 'fb.watch') or "
                             "contains(@href, 'tiktok.com')]"
                )
                
                if enlaces:
                    return enlaces[0].get_attribute('href')
            except:
                pass
            
            return None
            
        except:
            return None
    
    def _es_url_valida(self, url):
        """Verifica si la URL es de una plataforma válida"""
        dominios_validos = ['instagram.com', 'youtube.com', 'youtu.be', 'facebook.com', 'fb.watch', 'tiktok.com']
        return any(dominio in url for dominio in dominios_validos)
    
    def guardar_predicaciones(self, predicaciones):
        """Guarda las predicaciones en archivos individuales"""
        if not predicaciones:
            print("⚠️  No hay predicaciones para guardar")
            return
        
        print(f"\n💾 Guardando {len(predicaciones)} predicaciones...")
        
        for pred in predicaciones:
            numero = pred['numero']
            tipo = pred['tipo']
            contenido = pred['contenido']
            
            if tipo == 'enlace':
                nombre_archivo = f"predica-{numero:03d}.txt"
                ruta_archivo = os.path.join(self.carpeta_pendientes, nombre_archivo)
                
                with open(ruta_archivo, 'w', encoding='utf-8') as f:
                    f.write(contenido)
                
                print(f"  ✅ {nombre_archivo}")
        
        print(f"✅ Predicaciones guardadas en: {self.carpeta_pendientes}/\n")
    
    def ejecutar(self, nombre_grupo, cantidad=None, indice_inicio=0, solo_propios=True):
        """
        Método principal de ejecución
        Compatible con el sistema existente
        """
        if cantidad is None:
            cantidad = self.PREDICACIONES_OBJETIVO
        
        print(f"\n{N}{C}" + "="*70 + X)
        print(f"{N}{C}" + " " * 10 + "📱 EXTRACTOR DE PREDICACIONES - VERSIÓN FINAL" + X)
        print(f"{N}{C}" + "="*70 + X + "\n")
        
        try:
            if not self.iniciar_navegador():
                return []
            
            if not self.esperar_whatsapp_cargado():
                return []
            
            if not self.buscar_grupo(nombre_grupo):
                return []
            
            predicaciones = self.extraer_siguiente_lote(
                cantidad=cantidad,
                indice_inicio=indice_inicio,
                solo_propios=solo_propios
            )
            
            if predicaciones:
                self.guardar_predicaciones(predicaciones)
            
            return predicaciones
            
        finally:
            self.cerrar()
    
    def cerrar(self):
        """Cierra el navegador"""
        if self.driver:
            print("\n🔒 Cerrando navegador...")
            try:
                self.driver.quit()
                print("   ✅ Navegador cerrado")
            except:
                pass


if __name__ == "__main__":
    extractor = ExtractorWhatsAppPredicaciones()
    extractor.ejecutar("Prédicas")
