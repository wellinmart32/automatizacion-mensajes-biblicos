import os
import tkinter as tk
from compartido.toast import Toast
from tkinter import ttk, messagebox
import configparser
import re
import sys
import subprocess
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from gestor_licencias import GestorLicencias


class WizardPrimeraVez:
    """Wizard de configuración inicial para primera ejecución"""

    def __init__(self):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('AutomaPro.WizardMensajes')
        except Exception:
            pass

        self.root = tk.Tk()
        self.root.withdraw()

        self.root.title("🎉 Bienvenido - Mensajes Bíblicos")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f0f0")

        try:
            base_ico = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            self.root.iconbitmap(os.path.join(base_ico, 'iconos', 'wizard.ico'))
        except Exception:
            pass

        width = 600
        height = 500
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        # NO hacer deiconify aquí — se hará solo si necesita mostrar el wizard

        # Reaplicar icono múltiples veces para garantizar que Windows lo aplique
        try:
            base_ico = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            ico = os.path.join(base_ico, 'iconos', 'wizard.ico')
            self.root.after(100, lambda: self.root.iconbitmap(ico))
            self.root.after(300, lambda: self.root.iconbitmap(ico))
            self.root.after(500, lambda: self.root.iconbitmap(ico))
        except Exception:
            pass

        self.paso_actual = 0
        self.datos_config = {
            'codigo_licencia': '',
            'navegador': 'firefox',
            'usar_perfil': 'si',
            'usar_ejemplos': False
        }
        self.gestor_licencias = GestorLicencias()
        self.licencia_validada = False
        self.tipo_licencia = None

        # Si ya existe configuración, lanzar Panel de Control directamente sin mostrar wizard
        if self.gestor_licencias.obtener_codigo_guardado():
            try:
                if getattr(sys, 'frozen', False):
                    base_dir = os.path.dirname(sys.executable)
                    panel = os.path.join(base_dir, "PanelControl.exe")
                else:
                    panel = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel_control.py")
                if os.path.exists(panel):
                    if panel.endswith('.exe'):
                        subprocess.Popen([panel])
                    else:
                        subprocess.Popen([sys.executable, panel])
            except Exception:
                pass
            self.root.after(100, self.root.destroy)
            return

        # Solo mostrar el wizard si no hay configuración previa
        self.root.deiconify()
        self._mostrar_paso()

    def _limpiar_ventana(self):
        """Limpia todos los widgets de la ventana"""
        for widget in self.root.winfo_children():
            widget.destroy()

    def _mostrar_paso(self):
        """Muestra el paso actual del wizard"""
        self._limpiar_ventana()

        if self.paso_actual == 0:
            self._paso_bienvenida()
        elif self.paso_actual == 1:
            self._paso_licencia()
        elif self.paso_actual == 2:
            self._paso_configuracion()
        elif self.paso_actual == 3:
            self._paso_mensajes()
        elif self.paso_actual == 4:
            self._paso_finalizar()

    def _paso_bienvenida(self):
        """Paso 0: Pantalla de bienvenida"""
        # Header
        header = tk.Frame(self.root, bg="#1a73e8", pady=20)
        header.pack(fill='x')
        tk.Label(
            header,
            text="🎉 Bienvenido a Mensajes Bíblicos",
            font=("Segoe UI", 16, "bold"),
            bg="#1a73e8",
            fg="white"
        ).pack()

        # Contenido
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(fill='both', expand=True, padx=40, pady=30)

        tk.Label(
            frame,
            text="Esta aplicación publica mensajes bíblicos\nen Facebook de forma automática.",
            font=("Segoe UI", 12),
            bg="#f0f0f0",
            justify='center'
        ).pack(pady=(0, 20))

        tk.Label(
            frame,
            text="Vamos a configurarla juntos paso a paso\n(solo esta vez).",
            font=("Segoe UI", 11),
            bg="#f0f0f0",
            fg="gray",
            justify='center'
        ).pack(pady=(0, 30))

        tk.Label(
            frame,
            text="✨ Características:\n\n"
                 "• Publicación automática en Facebook\n"
                 "• Rotación inteligente de mensajes\n"
                 "• Integración con predicaciones de WhatsApp\n"
                 "• Programación de tareas (Versión Completa)",
            font=("Segoe UI", 10),
            bg="#f0f0f0",
            justify='left'
        ).pack(pady=(0, 30))

        # Botones
        frame_btn = tk.Frame(self.root, bg="#f0f0f0", pady=20)
        frame_btn.pack(fill='x', side='bottom')

        tk.Button(
            frame_btn,
            text="▶️  Comenzar",
            font=("Segoe UI", 11, "bold"),
            bg="#1a73e8",
            fg="white",
            width=20,
            command=self._siguiente
        ).pack()

    def _paso_licencia(self):
        """Paso 1: Activar licencia"""
        # Header
        header = tk.Frame(self.root, bg="#1a73e8", pady=15)
        header.pack(fill='x')
        tk.Label(
            header,
            text="Paso 1 de 4: Activar Licencia",
            font=("Segoe UI", 14, "bold"),
            bg="#1a73e8",
            fg="white"
        ).pack()

        # Contenido
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(fill='both', expand=True, padx=40, pady=20)

        # Campo email
        tk.Label(
            frame,
            text="Paso 1 — Ingresa tu email de AutomaPro:",
            font=("Segoe UI", 11, "bold"),
            bg="#f0f0f0"
        ).pack(anchor='w', pady=(0, 5))

        frame_email = tk.Frame(frame, bg="#f0f0f0")
        frame_email.pack(fill='x', pady=(0, 5))

        self.entry_email = tk.Entry(
            frame_email,
            font=("Segoe UI", 11),
            width=28,
            justify='center'
        )
        self.entry_email.pack(side='left', padx=(0, 5))
        self.entry_email.focus()

        self.btn_verificar_email = tk.Button(
            frame_email,
            text="Verificar",
            font=("Segoe UI", 9, "bold"),
            bg="#1a73e8",
            fg="white",
            command=self._verificar_email_wizard
        )
        self.btn_verificar_email.pack(side='left')

        self.label_estado_email = tk.Label(
            frame,
            text="",
            font=("Segoe UI", 9),
            bg="#f0f0f0"
        )
        self.label_estado_email.pack(anchor='w', pady=(0, 15))

        # Separador
        tk.Frame(frame, bg="#e0e0e0", height=1).pack(fill='x', pady=(0, 15))

        # Campo código — deshabilitado hasta verificar email
        tk.Label(
            frame,
            text="Paso 2 — ¿Tienes licencia completa? Ingresa tu código:",
            font=("Segoe UI", 11, "bold"),
            bg="#f0f0f0"
        ).pack(anchor='w', pady=(0, 5))

        tk.Label(
            frame,
            text="Si no tienes código, usa el botón 'Usar Prueba' abajo.",
            font=("Segoe UI", 9),
            bg="#f0f0f0",
            fg="gray"
        ).pack(anchor='w', pady=(0, 10))

        # Frame para el entry y el formato
        entry_frame = tk.Frame(frame, bg="#f0f0f0")
        entry_frame.pack(pady=(0, 5))
        
        self.entry_licencia = tk.Entry(
            entry_frame,
            font=("Segoe UI", 12, "bold"),
            width=20,
            justify='center',
            state='disabled'
        )
        self.entry_licencia.pack()
        
        # Label de formato esperado
        self.label_formato = tk.Label(
            frame,
            text="Formato: XXX-XXXXXX-XXXXX",
            font=("Segoe UI", 9),
            bg="#f0f0f0",
            fg="gray"
        )
        self.label_formato.pack(pady=(0, 20))
        
        # Forzar mayúsculas en cada tecla presionada
        def insertar_mayuscula(event):
            if event.char and event.char.isalpha():
                # Insertar la versión en mayúsculas
                pos = self.entry_licencia.index(tk.INSERT)
                self.entry_licencia.insert(pos, event.char.upper())
                return "break"
        
        # Auto-formateo con KeyRelease
        def auto_formateo(event):
            # Obtener contenido actual
            contenido = self.entry_licencia.get().upper()
            
            # Quitar guiones y caracteres no válidos
            solo_alfanum = re.sub(r'[^A-Z0-9]', '', contenido)
            
            # Resetear validación al editar
            if len(solo_alfanum) != 14:
                self.licencia_validada = False
                self.tipo_licencia = None
            
            # LÍMITE ESTRICTO: Cortar en 14 caracteres
            if len(solo_alfanum) > 14:
                solo_alfanum = solo_alfanum[:14]
            
            # Aplicar formato XXX-XXXXXX-XXXXX
            if len(solo_alfanum) <= 3:
                formateado = solo_alfanum
            elif len(solo_alfanum) <= 9:
                formateado = f"{solo_alfanum[:3]}-{solo_alfanum[3:]}"
            else:
                formateado = f"{solo_alfanum[:3]}-{solo_alfanum[3:9]}-{solo_alfanum[9:]}"
            
            # Solo actualizar si cambió
            if formateado != contenido:
                self.entry_licencia.delete(0, tk.END)
                self.entry_licencia.insert(0, formateado)
                # Cursor al final
                self.entry_licencia.icursor(tk.END)
            
            # Verificar licencia cuando tenga 14 caracteres
            if len(solo_alfanum) == 14:
                self._verificar_licencia_tiempo_real(formateado)
            elif len(solo_alfanum) > 0:
                self.label_formato.config(fg="#ffc107", text=f"⚠ Faltan {14 - len(solo_alfanum)} caracteres")
                self.licencia_validada = False
                self.tipo_licencia = None
            else:
                self.label_formato.config(fg="gray", text="Formato: XXX-XXXXXX-XXXXX")
                self.licencia_validada = False
                self.tipo_licencia = None
        
        # Bind para mayúsculas instantáneas
        self.entry_licencia.bind('<Key>', insertar_mayuscula)
        # Bind con KeyRelease para formateo
        self.entry_licencia.bind('<KeyRelease>', auto_formateo)

        tk.Label(
            frame,
            text="Si no tienes código, puedes usar la versión Prueba\n"
                 "(limitada a 5 mensajes por día)",
            font=("Segoe UI", 9),
            bg="#f0f0f0",
            fg="gray",
            justify='center'
        ).pack(pady=(0, 30))

        # Botones
        frame_btn = tk.Frame(self.root, bg="#f0f0f0", pady=20)
        frame_btn.pack(fill='x', side='bottom')

        tk.Button(
            frame_btn,
            text="◀️ Atrás",
            font=("Segoe UI", 10),
            bg="#e0e0e0",
            width=12,
            command=self._anterior
        ).pack(side='left', padx=(40, 10))

        self.btn_usar_prueba = tk.Button(
            frame_btn,
            text="Usar Prueba",
            font=("Segoe UI", 10),
            bg="#ffc107",
            width=12,
            command=self._usar_trial
        )
        self.btn_usar_prueba.pack(side='left', padx=10)

        tk.Button(
            frame_btn,
            text="Siguiente ▶️",
            font=("Segoe UI", 10, "bold"),
            bg="#28a745",
            fg="white",
            width=12,
            command=self._validar_licencia
        ).pack(side='right', padx=(10, 40))

    def _verificar_licencia_tiempo_real(self, codigo):
        """Verifica la licencia en tiempo real cuando se completa"""
        # Mostrar "Verificando..."
        self.label_formato.config(fg="gray", text="⏳ Verificando...")
        self.root.update()
        
        try:
            # Quitar guiones para validar longitud real
            codigo_limpio = re.sub(r'[^A-Z0-9]', '', codigo)
            
            # FORZAR LÍMITE ESTRICTO
            if len(codigo_limpio) != 14:
                self.label_formato.config(
                    fg="#dc3545",
                    text="❌ FORMATO INCORRECTO"
                )
                self.licencia_validada = False
                self.tipo_licencia = None
                return
            
            # Formatear correctamente
            codigo_formateado = f"{codigo_limpio[:3]}-{codigo_limpio[3:9]}-{codigo_limpio[9:]}"
            
            # Limpiar cache antes de verificar nueva licencia
            try:
                import json
                from pathlib import Path
                if os.name == 'nt':
                    base_path = Path(os.environ.get('USERPROFILE', '~'))
                else:
                    base_path = Path.home()

                # Limpiar cache principal
                archivo_config = base_path / '.config' / 'AutomaPro' / 'MensajesBiblicos' / 'config.json'
                if archivo_config.exists():
                    with open(archivo_config, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    if 'datos_licencia' in config:
                        del config['datos_licencia']
                        with open(archivo_config, 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)

                # Limpiar cache de respaldo en AppData
                archivo_respaldo = Path(os.environ.get('LOCALAPPDATA', '~')) / 'AutomaPro' / 'MensajesBiblicos' / 'lic.json'
                if archivo_respaldo.exists():
                    archivo_respaldo.unlink()
            except:
                pass
       
            # Verificar contra backend (sin cache)
            resultado = self.gestor_licencias.verificar_licencia(codigo_formateado, mostrar_mensajes=False, forzar_backend=True)
            
            if resultado['valida']:
                if resultado.get('developer_permanente'):
                    # Licencia MASTER - OCULTAR que es MASTER
                    self.label_formato.config(
                        fg="#28a745",
                        text="✅ LICENCIA COMPLETA VÁLIDA"
                    )
                    self.licencia_validada = True
                    self.tipo_licencia = 'MASTER'
                elif resultado.get('tipo') == 'FULL':
                    # Licencia FULL
                    self.label_formato.config(
                        fg="#28a745",
                        text="✅ LICENCIA COMPLETA VÁLIDA"
                    )
                    self.licencia_validada = True
                    self.tipo_licencia = 'FULL'
                elif resultado.get('tipo') == 'TRIAL':
                    # Licencia TRIAL
                    dias = resultado.get('diasRestantes', 0)
                    self.label_formato.config(
                        fg="#ffc107",
                        text=f"✅ LICENCIA PRUEBA ({dias} días restantes)"
                    )
                    self.licencia_validada = True
                    self.tipo_licencia = 'TRIAL'
                else:
                    # Tipo desconocido = inválida
                    self.label_formato.config(
                        fg="#dc3545",
                        text="❌ LICENCIA INVÁLIDA"
                    )
                    self.licencia_validada = False
                    self.tipo_licencia = None
            else:
                # Licencia inválida
                self.label_formato.config(
                    fg="#dc3545",
                    text="❌ LICENCIA INVÁLIDA"
                )
                self.licencia_validada = False
                self.tipo_licencia = None
        except Exception as e:
            print(f"Error verificando licencia: {e}")
            self.label_formato.config(
                fg="#dc3545",
                text="❌ Error al verificar"
            )
            self.licencia_validada = False
            self.tipo_licencia = None

    def _paso_configuracion(self):
        """Paso 2: Configuración básica"""
        header = tk.Frame(self.root, bg="#1a73e8", pady=15)
        header.pack(fill='x')
        tk.Label(
            header,
            text="Paso 2 de 4: Configuración",
            font=("Segoe UI", 14, "bold"),
            bg="#1a73e8",
            fg="white"
        ).pack()

        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(fill='both', expand=True, padx=40, pady=30)

        tk.Label(
            frame,
            text="Navegador:",
            font=("Segoe UI", 11, "bold"),
            bg="#f0f0f0"
        ).pack(anchor='w', pady=(0, 5))

        tk.Label(
            frame,
            text="(Se usará para Facebook, WhatsApp Oraciones y Extractor de Predicaciones)",
            font=("Segoe UI", 9),
            bg="#f0f0f0",
            fg="gray"
        ).pack(anchor='w', pady=(0, 10))

        self.var_navegador = tk.StringVar(value=self.datos_config.get('navegador', 'chrome'))
        frame_nav = tk.Frame(frame, bg="#f0f0f0")
        frame_nav.pack(anchor='w', pady=(0, 25))

        tk.Radiobutton(
            frame_nav, text="Firefox",
            variable=self.var_navegador, value="firefox",
            bg="#f0f0f0", font=("Segoe UI", 10)
        ).pack(side='left', padx=(0, 20))

        tk.Radiobutton(
            frame_nav, text="Chrome",
            variable=self.var_navegador, value="chrome",
            bg="#f0f0f0", font=("Segoe UI", 10)
        ).pack(side='left', padx=(0, 20))

        tk.Radiobutton(
            frame_nav, text="Edge",
            variable=self.var_navegador, value="edge",
            bg="#f0f0f0", font=("Segoe UI", 10)
        ).pack(side='left')

        tk.Label(
            frame,
            text="Usar tu sesión guardada:",
            font=("Segoe UI", 11, "bold"),
            bg="#f0f0f0"
        ).pack(anchor='w', pady=(0, 5))

        tk.Label(
            frame,
            text="(Recomendado: Sí - para no tener que iniciar sesión cada vez)",
            font=("Segoe UI", 9),
            bg="#f0f0f0",
            fg="gray"
        ).pack(anchor='w', pady=(0, 10))

        self.var_perfil = tk.StringVar(value=self.datos_config.get('usar_perfil', 'si'))
        frame_perfil = tk.Frame(frame, bg="#f0f0f0")
        frame_perfil.pack(anchor='w', pady=(0, 20))

        tk.Radiobutton(
            frame_perfil, text="Sí",
            variable=self.var_perfil, value="si",
            bg="#f0f0f0", font=("Segoe UI", 10)
        ).pack(side='left', padx=(0, 20))

        tk.Radiobutton(
            frame_perfil, text="No",
            variable=self.var_perfil, value="no",
            bg="#f0f0f0", font=("Segoe UI", 10)
        ).pack(side='left')

        frame_btn = tk.Frame(self.root, bg="#f0f0f0", pady=20)
        frame_btn.pack(fill='x', side='bottom')

        tk.Button(
            frame_btn,
            text="◀️ Atrás",
            font=("Segoe UI", 10),
            bg="#e0e0e0",
            width=12,
            command=self._anterior
        ).pack(side='left', padx=(40, 10))

        tk.Button(
            frame_btn,
            text="Siguiente ▶️",
            font=("Segoe UI", 10, "bold"),
            bg="#28a745",
            fg="white",
            width=12,
            command=self._guardar_config_basica
        ).pack(side='right', padx=(10, 40))

    def _paso_mensajes(self):
        """Paso 3: Crear mensajes o usar ejemplos"""
        # Header
        header = tk.Frame(self.root, bg="#1a73e8", pady=15)
        header.pack(fill='x')
        tk.Label(
            header,
            text="Paso 3 de 4: Tus Mensajes",
            font=("Segoe UI", 14, "bold"),
            bg="#1a73e8",
            fg="white"
        ).pack()

        # Contenido
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(fill='both', expand=True, padx=40, pady=30)

        # Verificar si ya hay mensajes
        mensajes_existentes = len([f for f in os.listdir('mensajes') if f.endswith('.txt')]) if os.path.exists('mensajes') else 0

        if mensajes_existentes > 0:
            tk.Label(
                frame,
                text=f"✅ Ya tienes {mensajes_existentes} mensajes creados",
                font=("Segoe UI", 12, "bold"),
                bg="#f0f0f0",
                fg="#28a745"
            ).pack(pady=(0, 10))
            
            tk.Label(
                frame,
                text="Puedes crear más mensajes o continuar con los que tienes.",
                font=("Segoe UI", 9),
                bg="#f0f0f0",
                fg="gray"
            ).pack(pady=(0, 20))
        else:
            tk.Label(
                frame,
                text="La aplicación necesita mensajes para publicar.",
                font=("Segoe UI", 11),
                bg="#f0f0f0"
            ).pack(pady=(0, 10))
            
            tk.Label(
                frame,
                text="Elige una de las opciones para continuar:",
                font=("Segoe UI", 9),
                bg="#f0f0f0",
                fg="gray"
            ).pack(pady=(0, 20))

        # Opción 1: Crear mensajes
        frame_op1 = tk.Frame(frame, bg="white", relief='solid', borderwidth=1)
        frame_op1.pack(fill='x', pady=(0, 15), padx=20)
        
        tk.Label(
            frame_op1,
            text="📝 Crear mensajes personalizados",
            font=("Segoe UI", 10, "bold"),
            bg="white"
        ).pack(anchor='w', padx=15, pady=(10, 5))
        
        tk.Label(
            frame_op1,
            text="Abre el gestor y crea tus propios mensajes bíblicos",
            font=("Segoe UI", 9),
            bg="white",
            fg="gray"
        ).pack(anchor='w', padx=15, pady=(0, 10))
        
        tk.Button(
            frame_op1,
            text="🖊️ Abrir Gestor de Mensajes",
            font=("Segoe UI", 9, "bold"),
            bg="#1a73e8",
            fg="white",
            command=self._abrir_gestor_mensajes
        ).pack(anchor='w', padx=15, pady=(0, 10))

        if mensajes_existentes == 0:
            # Opción 2: Ejemplos (solo si no hay mensajes)
            frame_op2 = tk.Frame(frame, bg="white", relief='solid', borderwidth=1)
            frame_op2.pack(fill='x', pady=(0, 15), padx=20)
            
            tk.Label(
                frame_op2,
                text="📋 Usar mensajes de ejemplo",
                font=("Segoe UI", 10, "bold"),
                bg="white"
            ).pack(anchor='w', padx=15, pady=(10, 5))
            
            tk.Label(
                frame_op2,
                text="Instala 5 mensajes bíblicos de ejemplo para comenzar rápidamente",
                font=("Segoe UI", 9),
                bg="white",
                fg="gray"
            ).pack(anchor='w', padx=15, pady=(0, 10))
            
            tk.Button(
                frame_op2,
                text="✨ Usar Ejemplos",
                font=("Segoe UI", 9, "bold"),
                bg="#28a745",
                fg="white",
                command=self._usar_ejemplos
            ).pack(anchor='w', padx=15, pady=(0, 10))

        # Botones
        frame_btn = tk.Frame(self.root, bg="#f0f0f0", pady=20)
        frame_btn.pack(fill='x', side='bottom')

        tk.Button(
            frame_btn,
            text="◀️ Atrás",
            font=("Segoe UI", 10),
            bg="#e0e0e0",
            width=12,
            pady=2,
            command=self._anterior
        ).pack(side='left', padx=(40, 10))

        tk.Button(
            frame_btn,
            text="Siguiente ▶️",
            font=("Segoe UI", 10, "bold"),
            bg="#28a745",
            fg="white",
            width=12,
            pady=2,
            command=self._verificar_mensajes
        ).pack(side='right', padx=(10, 40))

    def _paso_finalizar(self):
        """Paso 4: Finalizar configuración"""
        # Ajustar tamaño de ventana según tipo de licencia
        if self.tipo_licencia in ['FULL', 'MASTER']:
            nueva_altura = 720
        else:
            nueva_altura = 500
        
        # Redimensionar y recentrar FORZADO
        nueva_ancho = 600
        
        # Primero cambiar tamaño
        self.root.geometry(f"{nueva_ancho}x{nueva_altura}")
        
        # Forzar actualización para obtener dimensiones reales
        self.root.update_idletasks()
        
        # Calcular posición centrada
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - nueva_ancho) // 2
        y = (screen_height - nueva_altura) // 2
        
        # Aplicar posición centrada
        self.root.geometry(f'{nueva_ancho}x{nueva_altura}+{x}+{y}')
        
        # Forzar actualización visual
        self.root.update()
        
        # Header
        header = tk.Frame(self.root, bg="#28a745", pady=15)
        header.pack(fill='x')
        tk.Label(
            header,
            text="Paso 4 de 4: ¡Listo!",
            font=("Segoe UI", 14, "bold"),
            bg="#28a745",
            fg="white"
        ).pack()

        # Contenido
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(fill='both', expand=True, padx=40, pady=20)

        tk.Label(
            frame,
            text="✅ ¡Configuración completada!",
            font=("Segoe UI", 14, "bold"),
            bg="#f0f0f0",
            fg="#28a745"
        ).pack(pady=(0, 15))

        # Resumen
        resumen_frame = tk.Frame(frame, bg="white", relief='solid', borderwidth=1)
        resumen_frame.pack(fill='x', pady=(0, 15))

        licencia_texto = "Versión Completa ✅" if self.tipo_licencia in ['FULL', 'MASTER'] else "Período de Prueba (30 días)"
        mensajes_count = len([f for f in os.listdir('mensajes') if f.endswith('.txt')]) if os.path.exists('mensajes') else 0

        items = [
            ("✅ Licencia:", licencia_texto),
            ("✅ Navegador:", self.datos_config['navegador'].capitalize()),
            ("✅ Mensajes listos:", f"{mensajes_count} mensajes")
        ]

        for label, valor in items:
            item_frame = tk.Frame(resumen_frame, bg="white")
            item_frame.pack(fill='x', padx=15, pady=3)
            tk.Label(item_frame, text=label, font=("Segoe UI", 10, "bold"), bg="white", width=20, anchor='w').pack(side='left')
            tk.Label(item_frame, text=valor, font=("Segoe UI", 10), bg="white", anchor='w').pack(side='left')

        # Sección de tareas automáticas (solo FULL/MASTER)
        if self.tipo_licencia in ['FULL', 'MASTER']:
            # Separador
            separator = tk.Frame(frame, bg="#e0e0e0", height=2)
            separator.pack(fill='x', pady=15)
            
            # Título sección
            tk.Label(
                frame,
                text="🗓️ PROGRAMACIÓN AUTOMÁTICA (VERSIÓN COMPLETA)",
                font=("Segoe UI", 11, "bold"),
                bg="#f0f0f0",
                fg="#1a73e8"
            ).pack(pady=(0, 8))
            
            tk.Label(
                frame,
                text="¿Quieres que configuremos 4 publicaciones automáticas de mensajes bíblicos?",
                font=("Segoe UI", 9),
                bg="#f0f0f0"
            ).pack(pady=(0, 8))
            
            # Frame con horarios propuestos
            horarios_frame = tk.Frame(frame, bg="white", relief='solid', borderwidth=1)
            horarios_frame.pack(fill='x', pady=(0, 10))
            
            tk.Label(
                horarios_frame,
                text="Horarios propuestos:",
                font=("Segoe UI", 9, "bold"),
                bg="white",
                fg="gray"
            ).pack(anchor='w', padx=15, pady=(8, 3))
            
            horarios_texto = [
                "📅 Lunes y Jueves - 09:00 AM",
                "📅 Martes y Viernes - 02:00 PM", 
                "📅 Miércoles - 06:00 PM",
                "📅 Sábado - 11:00 AM"
            ]
            
            for horario in horarios_texto:
                tk.Label(
                    horarios_frame,
                    text=horario,
                    font=("Segoe UI", 9),
                    bg="white",
                    anchor='w'
                ).pack(anchor='w', padx=30, pady=1)
            
            tk.Label(
                horarios_frame,
                text="📖 Solo mensajes bíblicos (predicaciones se gestionan por separado)",
                font=("Segoe UI", 8),
                bg="white",
                fg="gray",
                anchor='w'
            ).pack(anchor='w', padx=30, pady=(3, 8))
            
            # Checkbox para activar
            self.var_crear_tareas = tk.BooleanVar(value=True)
            tk.Checkbutton(
                frame,
                text="✓ Sí, crear tareas automáticas",
                variable=self.var_crear_tareas,
                font=("Segoe UI", 10, "bold"),
                bg="#f0f0f0",
                fg="#28a745"
            ).pack(anchor='w', pady=(0, 8))

        tk.Label(
            frame,
            text="¿Quieres hacer la primera publicación ahora mismo?",
            font=("Segoe UI", 10),
            bg="#f0f0f0"
        ).pack(pady=(10, 5))

        # Botones
        frame_btn = tk.Frame(self.root, bg="#f0f0f0", pady=20)
        frame_btn.pack(fill='x', side='bottom')

        tk.Button(
            frame_btn,
            text="❌ Ahora no",
            font=("Segoe UI", 10),
            bg="#e0e0e0",
            width=15,
            command=self._finalizar_sin_publicar
        ).pack(side='left', padx=(40, 10))

        tk.Button(
            frame_btn,
            text="▶️ Publicar Ahora",
            font=("Segoe UI", 10, "bold"),
            bg="#28a745",
            fg="white",
            width=15,
            command=self._publicar_ahora
        ).pack(side='right', padx=(10, 40))

    # Funciones auxiliares
    def _siguiente(self):
        self.paso_actual += 1
        self._mostrar_paso()

    def _anterior(self):
        self.paso_actual -= 1
        self._mostrar_paso()

    def _verificar_email_wizard(self):
        """Verifica el email y determina el estado de la licencia del usuario"""
        email = self.entry_email.get().strip()
        if not email:
            messagebox.showwarning("Email requerido", "Ingresa tu email.")
            return

        self.label_estado_email.config(fg="gray", text="⏳ Verificando...")
        self.btn_verificar_email.config(state='disabled')
        self.root.update()

        try:
            url = self.gestor_licencias.url_backend.replace('/verificar-licencia', '/verificar-email')
            resp = requests.get(url, params={'email': email, 'nombreApp': 'MensajesBiblicos'}, timeout=30, verify=False)

            if resp.status_code != 200:
                self.label_estado_email.config(fg="#dc3545", text="❌ Error al verificar. Intenta nuevamente.")
                self.btn_verificar_email.config(state='normal')
                return

            datos = resp.json()

            if not datos.get('existe'):
                self.label_estado_email.config(fg="#dc3545", text="❌ Email no encontrado en AutomaPro.")
                messagebox.showerror("Email no registrado",
                    f"El email '{email}' no está registrado.\n\nRegístrate en:\nautomapro-frontend.vercel.app")
                self.btn_verificar_email.config(state='normal')
                return

            tipo = datos.get('tipoLicencia', 'NINGUNA')

            if tipo == 'FULL':
                # Tiene licencia completa — activar directamente y cachear
                self.label_estado_email.config(fg="#28a745", text="✅ Email verificado — Licencia Completa encontrada")
                codigo = datos.get('codigo', '')
                self.entry_licencia.config(state='normal')
                self.entry_licencia.delete(0, tk.END)
                self.entry_licencia.insert(0, codigo)
                self.entry_licencia.config(state='disabled')
                self.label_formato.config(fg="#28a745", text="✅ LICENCIA COMPLETA VÁLIDA")
                self.licencia_validada = True
                self.tipo_licencia = 'FULL'
                self.btn_verificar_email.config(state='disabled')
                if hasattr(self, 'btn_usar_prueba'):
                    self.btn_usar_prueba.config(state='disabled')
                # Cachear datos de licencia FULL para evitar verificación al abrir Panel
                self.gestor_licencias.guardar_codigo_licencia(codigo)
                self.gestor_licencias._guardar_cache_local({
                    'tipo': 'FULL',
                    'valida': True,
                    'expirado': False,
                    'diasRestantes': None,
                    'developer_permanente': False
                })

            elif tipo == 'TRIAL':
                dias = datos.get('diasRestantes', 0)
                expirado = datos.get('expirado', False)
                if expirado:
                    # Trial expirado — solo puede ingresar código de licencia completa
                    self.label_estado_email.config(fg="#dc3545", text="⚠️ Email verificado — Período de prueba expirado")
                    self.entry_licencia.config(state='normal')
                    self.label_formato.config(fg="#ffc107", text="Ingresa tu código de licencia completa")
                    self.btn_verificar_email.config(state='disabled')
                    # Bloquear botón Usar Prueba
                    if hasattr(self, 'btn_usar_prueba'):
                        self.btn_usar_prueba.config(state='disabled')
                else:
                    # Trial vigente
                    self.label_estado_email.config(fg="#28a745", text=f"✅ Email verificado — Prueba activa ({dias} días restantes)")
                    self.entry_licencia.config(state='normal')
                    self.label_formato.config(fg="gray", text="Opcional: ingresa código de licencia completa")
                    self.licencia_validada = True
                    self.tipo_licencia = 'TRIAL'
                    self.btn_verificar_email.config(state='disabled')

            elif tipo == 'NINGUNA':
                # Sin licencia — puede usar prueba
                self.label_estado_email.config(fg="#28a745", text="✅ Email verificado")
                self.entry_licencia.config(state='normal')
                self.label_formato.config(fg="gray", text="Opcional: ingresa código de licencia completa")
                self.btn_verificar_email.config(state='disabled')

        except Exception as e:
            self.label_estado_email.config(fg="#e65100", text="⏳ Servidor iniciando...")
            messagebox.showwarning(
                "Servidor iniciando",
                "El servidor está iniciando. Esto puede tomar hasta 2 minutos.\n\n"
                "Por favor espera un momento e intenta nuevamente."
            )
            self.btn_verificar_email.config(state='normal')

    def _usar_trial(self):
        """Registra automáticamente la instalación y obtiene código TRIAL"""
        email = self.entry_email.get().strip() if hasattr(self, 'entry_email') else None
        if not email:
            messagebox.showwarning("Email requerido", "Primero verifica tu email con el botón Verificar.")
            return
        # Verificar que el email fue verificado
        estado_email = self.label_estado_email.cget("text") if hasattr(self, 'label_estado_email') else ""
        if not estado_email or "❌" in estado_email:
            messagebox.showwarning("Email no verificado", "Primero verifica tu email con el botón Verificar.")
            return
        # Si ya tiene licencia completa no necesita usar prueba
        if self.tipo_licencia == 'FULL':
            messagebox.showinfo("Licencia Completa", "Ya tienes licencia completa activada. Da clic en Siguiente.")
            return
        self.label_formato.config(fg="gray", text="⏳ Activando período de prueba...")
        self.root.update()
        try:
            codigo = self.gestor_licencias.registrar_instalacion(email=email)
            if codigo:
                self.datos_config['codigo_licencia'] = codigo
                self.licencia_validada = True
                self.tipo_licencia = 'TRIAL'
                self.label_formato.config(fg="#28a745", text="✅ Período de prueba activado")
                self.root.after(1000, self._siguiente)
            else:
                self.label_formato.config(fg="#dc3545", text="❌ Error al activar. Verifica tu conexión.")
        except Exception as e:
            self.label_formato.config(fg="#dc3545", text=f"❌ Error: {e}")

    def _validar_licencia(self):
        codigo = self.entry_licencia.get().strip().upper()
        email = self.entry_email.get().strip() if hasattr(self, 'entry_email') else ""

        # Verificar que el email fue verificado
        estado_email = self.label_estado_email.cget("text") if hasattr(self, 'label_estado_email') else ""
        if not estado_email or "❌" in estado_email:
            messagebox.showwarning("Email no verificado", "Primero verifica tu email con el botón Verificar.")
            return

        # Si ya tiene licencia FULL activada automáticamente — avanzar directo
        if self.tipo_licencia == 'FULL' and self.licencia_validada:
            self.datos_config['codigo_licencia'] = self.entry_licencia.get().strip().upper()
            self.gestor_licencias.guardar_codigo_licencia(self.datos_config['codigo_licencia'])
            self._siguiente()
            return

        # Si tiene TRIAL vigente — avanzar directo
        if self.tipo_licencia == 'TRIAL' and self.licencia_validada and not codigo:
            self._siguiente()
            return

        # Si está vacío y no tiene licencia activa
        if not codigo:
            messagebox.showwarning(
                "Campo Vacío",
                "Debes ingresar un código de licencia o presionar 'Usar Prueba'."
            )
            return

        # Quitar guiones para validar
        codigo_limpio = re.sub(r'[^A-Z0-9]', '', codigo)

        # Validar formato (exactamente 14 caracteres)
        if len(codigo_limpio) != 14:
            messagebox.showerror(
                "Formato Incorrecto",
                f"El código debe tener exactamente 14 caracteres.\n\n"
                f"Formato: XXX-XXXXXX-XXXXX\n"
                f"Tienes: {len(codigo_limpio)} caracteres"
            )
            return

        # Validar que la licencia haya sido verificada y pertenezca al email
        if not self.licencia_validada:
            messagebox.showerror(
                "Licencia Inválida",
                "El código ingresado no es válido.\n\n"
                "Por favor verifica el código o usa Prueba."
            )
            return

        # Formatear correctamente
        codigo_formateado = f"{codigo_limpio[:3]}-{codigo_limpio[3:9]}-{codigo_limpio[9:]}"
        self.datos_config['codigo_licencia'] = codigo_formateado
        self.gestor_licencias.guardar_codigo_licencia(codigo_formateado)
        self._siguiente()

    def _guardar_config_basica(self):
        nav = self.var_navegador.get()
        self.datos_config['navegador'] = nav
        self.datos_config['usar_perfil'] = self.var_perfil.get()
        self.datos_config['navegador_whatsapp'] = nav
        self.datos_config['navegador_extractor'] = nav
        self._crear_config_completa()
        self._siguiente()

    def _abrir_gestor_mensajes(self):
        try:
            es_full = self.tipo_licencia in ['FULL', 'MASTER']

            if es_full:
                gestor_exe = os.path.join(os.path.dirname(sys.executable), 'GestorMensajes.exe')
                if os.path.exists(gestor_exe):
                    subprocess.Popen([gestor_exe])
                else:
                    messagebox.showwarning("Aviso", "El gestor de mensajes no se encontró.\nAbriendo carpeta de mensajes.")
                    subprocess.Popen(['explorer', os.path.abspath('mensajes')])
            else:
                gestor_exe = os.path.join(os.path.dirname(sys.executable), 'GestorMensajes.exe')
                if os.path.exists(gestor_exe):
                    subprocess.Popen([gestor_exe])
                else:
                    carpeta = os.path.abspath('mensajes')
                    os.makedirs(carpeta, exist_ok=True)
                    subprocess.Popen(['explorer', carpeta])
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el gestor: {e}")

    def _usar_ejemplos(self):
        try:
            os.makedirs('mensajes', exist_ok=True)
            
            # Verificar si ya existen archivos
            archivos_existentes = [f for f in os.listdir('mensajes') if f.startswith('ejemplo-') and f.endswith('.txt')]
            numero_inicio = len(archivos_existentes) + 1
            
            ejemplos = [
                "Confía en el Señor con todo tu corazón y no te apoyes en tu propia prudencia. - Proverbios 3:5",
                "Todo lo puedo en Cristo que me fortalece. - Filipenses 4:13",
                "El Señor es mi pastor, nada me faltará. - Salmos 23:1",
                "Mas buscad primeramente el reino de Dios y su justicia. - Mateo 6:33",
                "Porque de tal manera amó Dios al mundo, que ha dado a su Hijo unigénito. - Juan 3:16"
            ]
            
            archivos_creados = []
            for i, texto in enumerate(ejemplos, numero_inicio):
                nombre_archivo = f'ejemplo-{i:03d}.txt'
                with open(f'mensajes/{nombre_archivo}', 'w', encoding='utf-8') as f:
                    f.write(texto)
                archivos_creados.append(nombre_archivo)
            
            self.datos_config['usar_ejemplos'] = True
            messagebox.showinfo("✅ Éxito", f"Se instalaron {len(ejemplos)} mensajes de ejemplo:\n\n" + "\n".join(archivos_creados))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron crear los ejemplos: {e}")

    def _verificar_mensajes(self):
        mensajes = len([f for f in os.listdir('mensajes') if f.endswith('.txt')]) if os.path.exists('mensajes') else 0
        if mensajes == 0:
            messagebox.showwarning("Aviso", "Necesitas al menos un mensaje para continuar.\n\nCrea mensajes o usa los ejemplos.")
            return
        self._crear_config_completa()
        self._siguiente()

    def _crear_config_completa(self):
        """Crea el archivo config_global.txt con la configuración inicial completa"""
        config = configparser.ConfigParser()
        
        config['GENERAL'] = {
            'nombre_proyecto': 'Publicador Automático Facebook',
            'carpeta_mensajes': 'mensajes',
            'navegador': self.datos_config['navegador'],
            'modo_debug': 'si'
        }
        
        config['MENSAJES'] = {
            'seleccion': 'aleatorio',
            'relleno_hibrido': 'aleatorio',
            'cantidad_por_ejecucion': '1',
            'historial_evitar_repetir': '5',
            'formato_fecha': 'no',
            'agregar_hashtags': 'no',
            'hashtags': '#Fe,#Biblia,#Reflexión',
            'agregar_firma': 'no',
            'texto_firma': 'Publicado automáticamente'
        }
        
        config['PUBLICACION'] = {
            'tiempo_entre_intentos': '3',
            'max_intentos_por_publicacion': '3',
            'espera_despues_publicar': '5',
            'verificar_publicacion_exitosa': 'si',
            'espera_estabilizacion_modal': '3'
        }
        
        config['NAVEGADOR'] = {
            'usar_perfil_existente': self.datos_config['usar_perfil'],
            'carpeta_perfil_custom': 'perfiles/facebook_publicador',
            'desactivar_notificaciones': 'si',
            'maximizar_ventana': 'si'
        }
        
        config['LIMITES'] = {
            'tiempo_minimo_entre_publicaciones_segundos': '120',
            'permitir_duplicados': 'no',
            'permitir_forzar_publicacion_manual': 'si'
        }

        config['ORACIONES'] = {
            'navegador': self.datos_config.get('navegador_whatsapp', 'chrome')
        }
        
        config['PREDICACIONES'] = {
            'activar_predicaciones': 'no',
            'alternar_con_predicaciones': 'no',
            'nombre_grupo_whatsapp': '',
            'mensajes_por_extraccion': '10',
            'navegador': self.datos_config.get('navegador_extractor', 'chrome'),
            'agregar_introduccion_predica': 'si',
            'texto_introduccion_predica': '⏰ Vale la pena ver esto',
            'agregar_hashtags_predicaciones': 'no',
            'hashtags_predicaciones': '',
            'tiempo_espera_previsualizacion': '12',
            'usar_estrategia_optimizada_enlaces': 'si'
        }
        
        config['DEBUG'] = {
            'modo_debug': 'detallado'
        }
        
        with open('config_global.txt', 'w', encoding='utf-8') as f:
            f.write("# ============================================================\n")
            f.write("# CONFIGURACIÓN GLOBAL - PUBLICADOR AUTOMÁTICO FACEBOOK\n")
            f.write("# ============================================================\n\n")
            config.write(f)

    def _crear_tareas_predeterminadas(self):
        """Crea las 4 tareas automáticas predeterminadas"""
        try:
            prefijo = "AutomaPro_MensajesBiblicos"

            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
                exe = os.path.join(base_dir, "MensajesBiblicos.exe")
                plantilla_comando = f'"{exe}" --tarea={{id}}'
            else:
                ruta_script = os.path.abspath("publicar_facebook.py")
                directorio_trabajo = os.path.dirname(ruta_script)
                plantilla_comando = f'cmd /c "cd /d "{directorio_trabajo}" && py "{ruta_script}" --tarea={{id}}"'
            
            # Definir las 4 tareas
            tareas = [
                {
                    'nombre': f"{prefijo}_LunesJueves",
                    'dias': 'MON,THU',
                    'hora': '09:00'
                },
                {
                    'nombre': f"{prefijo}_MartesViernes",
                    'dias': 'TUE,FRI',
                    'hora': '14:00'
                },
                {
                    'nombre': f"{prefijo}_Miercoles",
                    'dias': 'WED',
                    'hora': '18:00'
                },
                {
                    'nombre': f"{prefijo}_Sabado",
                    'dias': 'SAT',
                    'hora': '11:00'
                }
            ]
            
            tareas_creadas = 0
            errores = []
            
            for tarea in tareas:
                comando = [
                    'schtasks',
                    '/Create',
                    '/TN', tarea['nombre'],
                    '/TR', plantilla_comando.format(id=tarea['nombre'][len(prefijo) + 1:]),
                    '/SC', 'WEEKLY',
                    '/D', tarea['dias'],
                    '/ST', tarea['hora'],
                    '/F'
                ]
                
                resultado = subprocess.run(
                    comando,
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if resultado.returncode == 0:
                    tareas_creadas += 1
                else:
                    errores.append(tarea['nombre'])
            
            if tareas_creadas > 0:
                self._mostrar_toast(
                    f"✅ Se crearon {tareas_creadas} tareas automáticas\n\nPuedes verlas en el Gestor de Tareas",
                    duracion=4000,
                    color="#28a745"
                )
            
            if errores:
                messagebox.showwarning(
                    "⚠️ Advertencia",
                    f"No se pudieron crear {len(errores)} tareas:\n" + "\n".join(errores)
                )
        
        except Exception as e:
            messagebox.showerror("Error", f"Error creando tareas automáticas:\n{e}")

    def _finalizar_sin_publicar(self):
        # Crear tareas automáticas si está activado
        if hasattr(self, 'var_crear_tareas') and self.var_crear_tareas.get():
            self._crear_tareas_predeterminadas()
            # Esperar a que se muestre el toast de tareas
            self.root.after(4500, lambda: self._mostrar_mensaje_final_y_cerrar())
        else:
            self._mostrar_mensaje_final_y_cerrar()

    def _mostrar_mensaje_final_y_cerrar(self):
        """Muestra el mensaje final como toast y cierra el wizard"""
        self._mostrar_toast(
            "¡Todo listo!\n\nPuedes ejecutar 'Mensajes Bíblicos' cuando quieras publicar.",
            duracion=3000,
            color="#28a745"
        )
        self.root.after(3000, self.root.destroy)

    def _publicar_ahora(self):
        try:
            # Crear tareas automáticas si está activado
            if hasattr(self, 'var_crear_tareas') and self.var_crear_tareas.get():
                self._crear_tareas_predeterminadas()

            base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            exe = os.path.join(base, 'MensajesBiblicos.exe')
            if os.path.exists(exe):
                subprocess.Popen([exe])
            else:
                subprocess.Popen([sys.executable, 'publicar_facebook.py'])
            self._mostrar_toast(
                "🚀 Publicación Iniciada\n\nEl navegador se abrirá en unos segundos...",
                duracion=3000,
                color="#28a745"
            )
            # Cerrar wizard después de 3 segundos
            self.root.after(3000, self.root.destroy)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar la publicación: {e}")

    def _mostrar_toast(self, mensaje, duracion=3000, color="#28a745"):
        """Delega al sistema centralizado de toasts"""
        from compartido.toast import Toast
        if color == Toast.COLOR_ERROR or color == "#dc3545":
            Toast.error(self.root, mensaje, duracion)
        elif color == Toast.COLOR_ADVERTENCIA or color == "#e65100":
            Toast.advertencia(self.root, mensaje, duracion)
        elif color == Toast.COLOR_INFO or color == "#1a73e8":
            Toast.info(self.root, mensaje, duracion)
        else:
            Toast.exito(self.root, mensaje, duracion)

    def ejecutar(self):
        self.root.mainloop()


def main():
    wizard = WizardPrimeraVez()
    wizard.ejecutar()


if __name__ == "__main__":
    main()