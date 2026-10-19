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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
import pyperclip
import time
import os


class PublicadorFacebook:
    """Automatización de publicaciones en Facebook"""

    def __init__(self, config):
        self.driver = None
        self.wait = None
        self.config = config

    def iniciar_navegador(self):
        navegador = self.config['navegador']
        print(f"{N}🌐 Iniciando {navegador.upper()}...{X}")
        if navegador == 'firefox':
            self._iniciar_firefox()
        elif navegador in ('chrome', 'edge'):
            self._iniciar_chromium(navegador)
        else:
            raise Exception(f"Navegador no soportado: {navegador}")
        self.wait = WebDriverWait(self.driver, 20)
        if self.config['maximizar_ventana']:
            self.driver.maximize_window()
        print(f"   {V}✅ Navegador iniciado{X}")

    def _iniciar_firefox(self):
        import sys
        import subprocess
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        perfil_fallback = os.path.join(base_dir, "perfiles", "firefox_facebook")
        os.makedirs(perfil_fallback, exist_ok=True)

        # Detectar si Firefox ya está corriendo
        try:
            resultado = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq firefox.exe', '/NH'],
                capture_output=True, text=True
            )
            firefox_ya_abierto = 'firefox.exe' in resultado.stdout.lower()
        except Exception:
            firefox_ya_abierto = False

        usar_perfil = self.config.get('usar_perfil_existente', True)
        if usar_perfil and not firefox_ya_abierto:
            from compartido.gestor_archivos import obtener_ruta_perfil_navegador
            ruta_perfil = obtener_ruta_perfil_navegador()
            if ruta_perfil:
                opciones = FirefoxOptions()
                if self.config['desactivar_notificaciones']:
                    opciones.set_preference("dom.webnotifications.enabled", False)
                opciones.add_argument("-profile")
                opciones.add_argument(ruta_perfil)
                try:
                    self.driver = webdriver.Firefox(options=opciones)
                    return
                except Exception as e:
                    print(f"   ⚠️  Perfil principal bloqueado ({e}), usando perfil dedicado...")
        elif firefox_ya_abierto:
            print(f"   ℹ️  Firefox ya está abierto, usando perfil dedicado...")

        opciones = FirefoxOptions()
        if self.config['desactivar_notificaciones']:
            opciones.set_preference("dom.webnotifications.enabled", False)
        opciones.add_argument("-profile")
        opciones.add_argument(perfil_fallback)
        print(f"   ✓ Usando perfil dedicado: {perfil_fallback}")
        self.driver = webdriver.Firefox(options=opciones)

    def _iniciar_chromium(self, navegador):
        """Chrome y Edge comparten motor (Chromium): misma lógica, distinta clase de Selenium"""
        import sys
        import subprocess
        import tempfile

        if navegador == 'edge':
            # Microsoft cerró el servidor antiguo de msedgedriver; versiones viejas de Selenium Manager lo seguían usando
            os.environ.setdefault("SE_DRIVER_MIRROR_URL", "https://msedgedriver.microsoft.com")
            from selenium.webdriver.edge.options import Options as OpcionesNavegador
            clase_driver = webdriver.Edge
            proceso, nombre = 'msedge.exe', 'Edge'
        else:
            OpcionesNavegador = ChromeOptions
            clase_driver = webdriver.Chrome
            proceso, nombre = 'chrome.exe', 'Chrome'

        def _opciones_base():
            op = OpcionesNavegador()
            if self.config['desactivar_notificaciones']:
                op.add_argument("--disable-notifications")
            op.add_argument("--disable-blink-features=AutomationControlled")
            # enable-logging y log-level evitan que el navegador llene la consola con mensajes internos
            op.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            op.add_argument("--log-level=3")
            op.add_experimental_option('useAutomationExtension', False)
            op.add_argument("--no-first-run")
            op.add_argument("--no-default-browser-check")
            op.add_argument("--disable-session-crashed-bubble")
            op.add_argument("--hide-crash-restore-bubble")
            op.add_argument("--disable-features=InfiniteSessionRestore")
            op.add_experimental_option("prefs", {
                "profile.exit_type": "Normal",
                "profile.exited_cleanly": True
            })
            return op

        # Detectar si el navegador ya está corriendo
        try:
            resultado = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq {proceso}', '/NH'],
                capture_output=True, text=True
            )
            ya_abierto = proceso in resultado.stdout.lower()
        except Exception:
            ya_abierto = False

        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        perfil_dedicado = os.path.join(base_dir, "perfiles", f"{navegador}_facebook")
        os.makedirs(perfil_dedicado, exist_ok=True)

        usar_perfil = self.config.get('usar_perfil_existente', True)

        if ya_abierto:
            print(f"   ℹ️  {nombre} ya está abierto, iniciando instancia separada con perfil dedicado...")

        if usar_perfil:
            opciones = _opciones_base()
            opciones.add_argument(f"--user-data-dir={perfil_dedicado}")
            try:
                self.driver = clase_driver(options=opciones)
                return
            except Exception as e:
                print(f"   ⚠️  No se pudo abrir con el perfil dedicado ({e}), usando perfil temporal...")

        perfil_tmp = tempfile.mkdtemp(prefix=f"{navegador}_fb_tmp_")
        opciones = _opciones_base()
        opciones.add_argument(f"--user-data-dir={perfil_tmp}")
        self.driver = clase_driver(options=opciones)

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

    def _es_pagina_seguridad_facebook(self):
        """Detecta si Facebook mostró una página de verificación de seguridad"""
        url_actual = self.driver.current_url
        urls_seguridad = [
            'two_step_verification',
            'checkpoint',
            'login/device-based',
            'security_check',
            'identity_confirmation',
            'recaptcha',
            'captcha'
        ]
        return any(p in url_actual for p in urls_seguridad)

    def _esperar_resolucion_seguridad(self, timeout=180):
        """
        Espera a que el usuario resuelva el puzzle de seguridad de Facebook.
        Retorna True si el usuario lo resolvió, False si se agotó el tiempo.
        """
        tiempo_transcurrido = 0
        while tiempo_transcurrido < timeout:
            time.sleep(5)
            tiempo_transcurrido += 5
            try:
                url_actual = self.driver.current_url
                # Si ya salió de la página de seguridad y no está en login → resuelto
                if not self._es_pagina_seguridad_facebook()\
                        and 'login' not in url_actual\
                        and 'facebook.com' in url_actual:
                    print(f"{V}✅ Verificación de seguridad resuelta correctamente{X}")
                    time.sleep(3)
                    return True
                else:
                    restantes = timeout - tiempo_transcurrido
                    print(f"⏳ Esperando que resuelvas el puzzle... ({restantes}s restantes)")
            except Exception:
                return True
        print(f"\n{R}❌ Tiempo de espera agotado para resolver el puzzle.{X}")
        return False

    def verificar_sesion_facebook(self):
        print(f"{N}🔐 Verificando sesión de Facebook...{X}")
        try:
            self.driver.get("https://www.facebook.com")
            time.sleep(3)

            # Caso 1: Página de seguridad/captcha de Facebook
            if self._es_pagina_seguridad_facebook():
                self._notificar_login(
                    "Verificación de seguridad requerida",
                    "Facebook pide que resuelvas un puzzle de seguridad.\n"
                    "Resuélvelo en el navegador.\nTienes 3 minutos."
                )
                print(f"\n{A}{N}⚠️  FACEBOOK REQUIERE VERIFICACIÓN DE SEGURIDAD{X}")
                print(f"{A}" + "=" * 60 + X)
                print(f"{A}Facebook detectó actividad inusual y pide verificación.{X}")
                print(f"{A}Por favor resuelve el puzzle en el navegador.{X}")
                print(f"{A}Tienes 3 MINUTOS para completarlo.{X}")
                print(f"{A}" + "=" * 60 + X + "\n")
                return self._esperar_resolucion_seguridad(timeout=180)

            # Caso 2: Formulario de login normal
            try:
                login_elements = self.driver.find_elements(By.XPATH,
                    "//input[@name='email' or @name='pass']")
                if len(login_elements) > 0:
                    self._notificar_login(
                        "Iniciar sesión en Facebook",
                        "Ingresa tus credenciales.\nTienes 2 minutos."
                    )
                    print(f"\n{A}{N}⚠️  NO HAS INICIADO SESIÓN EN FACEBOOK{X}")
                    print(f"{A}" + "=" * 60 + X)
                    print(f"{A}Por favor INICIA SESIÓN en Facebook ahora.{X}")
                    print(f"{A}Tienes 2 MINUTOS para iniciar sesión.{X}")
                    print(f"{A}" + "=" * 60 + X + "\n")
                    timeout = 120
                    tiempo_transcurrido = 0
                    while tiempo_transcurrido < timeout:
                        time.sleep(5)
                        tiempo_transcurrido += 5
                        try:
                            # Verificar si apareció página de seguridad después del login
                            if self._es_pagina_seguridad_facebook():
                                print(f"\n{A}⚠️  Facebook pide verificación adicional...{X}")
                                self._notificar_login(
                                    "Verificación de seguridad requerida",
                                    "Facebook pide que resuelvas un puzzle.\n"
                                    "Resuélvelo en el navegador.\nTienes 3 minutos."
                                )
                                return self._esperar_resolucion_seguridad(timeout=180)

                            login_check = self.driver.find_elements(By.XPATH,
                                "//input[@name='email' or @name='pass']")
                            if len(login_check) == 0:
                                print(f"{V}✅ Sesión iniciada correctamente{X}")
                                time.sleep(3)
                                return True
                            else:
                                print(f"⏳ Esperando login... ({timeout - tiempo_transcurrido}s restantes)")
                        except Exception:
                            print("✅ Sesión iniciada correctamente")
                            time.sleep(3)
                            return True
                    print(f"\n{R}❌ Tiempo de espera agotado.{X}")
                    return False
                else:
                    print(f"{V}✅ Ya tienes sesión activa en Facebook{X}")
                    return True
            except Exception:
                print("✅ Ya tienes sesión activa en Facebook")
                return True
        except Exception as e:
            print(f"⚠️  Error verificando sesión: {e}")
            return True

    def abrir_compositor(self):
        print("📝 Abriendo compositor de publicación...")
        url_actual = self.driver.current_url
        if "facebook.com" not in url_actual:
            self.driver.get("https://www.facebook.com")
            time.sleep(5)
        elif "stories" in url_actual or "watch" in url_actual or "?sk=" in url_actual:
            self.driver.get("https://www.facebook.com")
            time.sleep(5)

        # Estrategia 1: Selector exacto
        try:
            selector_exacto = "//div[@role='button']//span[@class='x1lliihq x6ikm8r x10wlt62 x1n2onr6' and contains(text(), 'pensando')]"
            botones = self.driver.find_elements(By.XPATH, selector_exacto)
            if botones:
                for boton_span in botones:
                    try:
                        boton = boton_span.find_element(By.XPATH, "./ancestor::div[@role='button']")
                        if boton.is_displayed():
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", boton)
                            time.sleep(1.5)
                            self.driver.execute_script("arguments[0].click();", boton)
                            try:
                                WebDriverWait(self.driver, 5).until(
                                    EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
                                )
                                time.sleep(self.config.get('espera_estabilizacion_modal', 3))
                                return True
                            except:
                                pass
                    except:
                        continue
        except:
            pass

        # Estrategia 2: Contenedor región
        try:
            contenedor = self.driver.find_element(By.XPATH,
                "//div[@role='region' and @aria-label='Crear una publicación']")
            boton = contenedor.find_element(By.XPATH, ".//div[@role='button' and contains(., 'pensando')]")
            if boton.is_displayed():
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton)
                time.sleep(1.5)
                self.driver.execute_script("arguments[0].click();", boton)
                time.sleep(3)
                dialogs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']")
                if dialogs and dialogs[0].is_displayed():
                    time.sleep(self.config.get('espera_estabilizacion_modal', 3))
                    return True
        except:
            pass

        # Estrategia 3: Span con texto
        for selector in [
            "//span[contains(text(), '¿Qué estás pensando, Wellington?')]",
            "//span[contains(text(), 'pensando, Wellington')]",
            "//span[contains(text(), '¿Qué estás pensando')]"
        ]:
            try:
                spans = self.driver.find_elements(By.XPATH, selector)
                for span in spans:
                    try:
                        if not span.is_displayed():
                            continue
                        boton = span.find_element(By.XPATH, "./ancestor::div[@role='button']")
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", boton)
                        time.sleep(3)
                        dialogs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']")
                        if dialogs and dialogs[0].is_displayed():
                            time.sleep(self.config.get('espera_estabilizacion_modal', 3))
                            return True
                    except:
                        continue
            except:
                continue

        # Estrategia 4: Todos los botones
        try:
            for boton in self.driver.find_elements(By.XPATH, "//div[@role='button']")[:30]:
                try:
                    if not boton.is_displayed():
                        continue
                    if 'pensando' in boton.text.strip().lower():
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", boton)
                        time.sleep(3)
                        if self.driver.find_elements(By.XPATH, "//div[@role='dialog']"):
                            time.sleep(self.config.get('espera_estabilizacion_modal', 3))
                            return True
                except:
                    continue
        except:
            pass

        # Estrategia 5: Scroll al inicio
        try:
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            for span in self.driver.find_elements(By.XPATH, "//span[contains(text(), 'pensando')]"):
                try:
                    if span.is_displayed():
                        boton = span.find_element(By.XPATH, "./ancestor::div[@role='button']")
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", boton)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", boton)
                        time.sleep(3)
                        if self.driver.find_elements(By.XPATH, "//div[@role='dialog']"):
                            time.sleep(self.config.get('espera_estabilizacion_modal', 3))
                            return True
                except:
                    continue
        except:
            pass

        # Estrategia 6: Atajo teclado
        try:
            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(1)
            ActionChains(self.driver).send_keys('p').perform()
            time.sleep(3)
            if self.driver.find_elements(By.XPATH, "//div[@role='dialog']"):
                time.sleep(self.config.get('espera_estabilizacion_modal', 3))
                return True
        except:
            pass

        print("❌ No se pudo abrir el compositor")
        return False

    def ingresar_texto(self, mensaje):
        print("✍️  Ingresando texto...")
        area_texto = self._buscar_area_texto()
        if not area_texto:
            print("   ❌ No se encontró área de texto")
            return False

        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", area_texto)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].focus();", area_texto)
            time.sleep(1)
        except:
            pass

        def _verificar_texto(el):
            try:
                contenido = self.driver.execute_script(
                    "return arguments[0].innerText || arguments[0].textContent || '';", el)
                return len(contenido.strip()) >= 10
            except:
                return False

        # Método 1: Portapapeles
        try:
            pyperclip.copy(mensaje)
            self.driver.execute_script("arguments[0].focus();", area_texto)
            time.sleep(0.5)
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(2)
            if _verificar_texto(area_texto):
                print("   ✅ Texto ingresado")
                return True
        except Exception as e:
            print(f"   ⚠️  Error portapapeles: {e}")

        # Método 2: send_keys
        try:
            self.driver.execute_script("arguments[0].focus();", area_texto)
            time.sleep(0.5)
            ActionChains(self.driver).send_keys(mensaje).perform()
            time.sleep(2)
            if _verificar_texto(area_texto):
                print("   ✅ Texto ingresado")
                return True
        except Exception as e:
            print(f"   ⚠️  Error send_keys: {e}")

        # Método 3: JavaScript
        try:
            self.driver.execute_script("""
                arguments[0].focus();
                arguments[0].textContent = arguments[1];
                arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
            """, area_texto, mensaje)
            time.sleep(2)
            if _verificar_texto(area_texto):
                print("   ✅ Texto ingresado")
                return True
        except Exception as e:
            print(f"   ❌ Error JavaScript: {e}")

        print("   ❌ No se pudo ingresar texto")
        return False

    def _buscar_area_texto(self):
        for sel in [
            "//div[@role='dialog']//div[@contenteditable='true']",
            "//div[@contenteditable='true'][@role='textbox']",
            "//div[@contenteditable='true']",
        ]:
            try:
                elemento = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.XPATH, sel))
                )
                time.sleep(1.5)
                return elemento
            except:
                continue
        return None

    def publicar_mensaje(self):
        print("🚀 Publicando...")
        time.sleep(2)
        boton_encontrado = False

        for selector in [
            "//div[@aria-label='Publicar']",
            "//div[@role='button' and contains(text(), 'Publicar')]",
            "//span[text()='Publicar']/ancestor::div[@role='button']",
            "//div[@role='button']//span[text()='Publicar']"
        ]:
            try:
                for elemento in self.driver.find_elements(By.XPATH, selector):
                    try:
                        if elemento.is_displayed() and elemento.is_enabled():
                            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elemento)
                            time.sleep(1)
                            self.driver.execute_script("arguments[0].click();", elemento)
                            boton_encontrado = True
                            break
                    except:
                        continue
                if boton_encontrado:
                    break
            except:
                continue

        if not boton_encontrado:
            try:
                for elemento in self.driver.find_elements(By.XPATH, "//div[@role='button']"):
                    try:
                        if elemento.text.strip().lower() == "publicar":
                            self.driver.execute_script("arguments[0].click();", elemento)
                            boton_encontrado = True
                            break
                    except:
                        continue
            except:
                pass

        if not boton_encontrado:
            try:
                dialog = self.driver.find_element(By.XPATH, "//div[@role='dialog']")
                boton = dialog.find_element(By.XPATH, ".//div[@role='button' and contains(., 'Publicar')]")
                self.driver.execute_script("arguments[0].click();", boton)
                boton_encontrado = True
            except:
                pass

        if not boton_encontrado:
            print("   ❌ No se encontró botón 'Publicar'")
            return False

        print(f"   ✅ Publicado")
        time.sleep(self.config['espera_despues_publicar'])
        return True

    def verificar_publicacion_exitosa(self):
        if not self.config['verificar_publicacion_exitosa']:
            return True
        try:
            dialogs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']")
            if len(dialogs) == 0:
                return True
            time.sleep(3)
            return len(self.driver.find_elements(By.XPATH, "//div[@role='dialog']")) == 0
        except:
            return True

    def publicar_enlace_con_preview_optimizado(self, enlace, texto_introduccion="", hashtags=""):
        print("\n🔗 Publicando enlace con previsualización...")
        area_texto = self._buscar_area_texto()
        if not area_texto:
            print("   ❌ No se encontró área de texto")
            return False

        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", area_texto)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", area_texto)
            time.sleep(1)
            self.driver.execute_script("arguments[0].focus();", area_texto)
            time.sleep(1)
            area_texto.send_keys(Keys.CONTROL + "a")
            time.sleep(0.3)
            area_texto.send_keys(Keys.DELETE)
            time.sleep(0.5)
        except Exception as e:
            print(f"   ⚠️  Error dando foco: {e}")

        if texto_introduccion:
            try:
                for caracter in texto_introduccion:
                    area_texto.send_keys(caracter)
                    time.sleep(0.02)
                area_texto.send_keys(Keys.RETURN)
                time.sleep(0.2)
                area_texto.send_keys(Keys.RETURN)
                time.sleep(0.3)
            except Exception as e:
                print(f"   ⚠️  Error escribiendo introducción: {e}")

        try:
            pyperclip.copy(enlace)
            time.sleep(0.5)
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(2)
        except Exception as e:
            print(f"   ❌ Error pegando enlace: {e}")
            return False

        tiempo_espera = self.config.get('tiempo_espera_previsualizacion', 12)
        print(f"⏳ Esperando previsualización ({tiempo_espera}s)...")
        for i in range(tiempo_espera, 0, -1):
            if i % 2 == 0:
                print(f"   {i}s restantes", end='\r', flush=True)
            time.sleep(1)

        if hashtags:
            try:
                time.sleep(1)
                area_texto = self._buscar_area_texto()
                if area_texto:
                    ActionChains(self.driver).key_down(Keys.CONTROL).send_keys(Keys.END).key_up(Keys.CONTROL).perform()
                    time.sleep(0.5)
                    area_texto.send_keys(Keys.RETURN)
                    time.sleep(0.2)
                    area_texto.send_keys(Keys.RETURN)
                    time.sleep(0.2)
                    for caracter in hashtags.strip():
                        area_texto.send_keys(caracter)
                        time.sleep(0.05)
                        if caracter == '#':
                            time.sleep(0.3)
                            area_texto.send_keys(Keys.ESCAPE)
                            time.sleep(0.2)
            except Exception as e:
                print(f"   ⚠️  Error agregando hashtags: {e}")

        if not self.publicar_mensaje():
            print("❌ Error al publicar")
            return False

        self.verificar_publicacion_exitosa()
        print("✅ Publicación completada")
        return True

    def publicar_completo(self, mensaje):
        try:
            if not self.verificar_sesion_facebook():
                print("❌ No se pudo verificar sesión")
                return False
            if not self.abrir_compositor():
                print("❌ No se pudo abrir compositor")
                return False
            if not self.ingresar_texto(mensaje):
                print("❌ No se pudo ingresar texto")
                return False
            if not self.publicar_mensaje():
                print("❌ No se pudo publicar")
                return False
            self.verificar_publicacion_exitosa()
            print("✅ Publicación completada")
            return True
        except Exception as e:
            print(f"❌ Error durante publicación: {e}")
            import traceback
            traceback.print_exc()
            return False

    def cerrar_navegador(self):
        if self.driver:
            print("\n🔒 Cerrando navegador...")
            try:
                self.driver.quit()
                print(f"   {V}✅ Navegador cerrado{X}")
            except:
                pass