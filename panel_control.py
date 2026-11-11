import os
import sys
import tkinter as tk
from tkinter import messagebox
import subprocess
from gestor_licencias import GestorLicencias
from gestor_registro import GestorRegistro
from compartido.gestor_archivos import migrar_tareas_antiguas, problema_fuentes_predicaciones
from compartido.toast import Toast


class PanelControl:
    """Panel de control principal - Mensajes Bíblicos"""

    def __init__(self):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('AutomaPro.PanelControlMensajes')
        except Exception:
            pass

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("📘 Mensajes Bíblicos - Panel de Control")
        self.root.geometry("700x680")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f0f0")

        try:
            base_ico = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            ico = os.path.join(base_ico, 'iconos', 'dashboard.ico')
            self.root.iconbitmap(ico)
            # default= hace que las subventanas (Toplevel) hereden el ícono en vez de la pluma de Tkinter
            self.root.iconbitmap(default=ico)
        except Exception:
            pass

        self.gestor_licencias = GestorLicencias()
        self.licencia = self._verificar_licencia()

        # Ruta base del ejecutable
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        if not self.licencia:
            self.root.destroy()
            return

        self._construir_ui()

        # Centrar después de construir la UI completa
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        self.root.deiconify()

        self._verificar_actualizacion()
        self._migrar_tareas_en_segundo_plano()

    def _migrar_tareas_en_segundo_plano(self):
        """Convierte en silencio las tareas automáticas antiguas al formato con --tarea"""
        import threading
        def migrar():
            try:
                migradas = migrar_tareas_antiguas()
            except Exception as e:
                print(f"⚠️  Error actualizando tareas automáticas: {e}")
                return
            if migradas:
                self.root.after(0, lambda: self._toast("🔄 Tareas automáticas actualizadas",
                                                       f"{migradas} tarea(s) convertida(s) al formato nuevo"))
        threading.Thread(target=migrar, daemon=True).start()

    def _exe(self, nombre):
        """Retorna ruta al .exe en la misma carpeta del ejecutable"""
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, nombre)

    def _verificar_licencia(self):
        """Verifica licencia — usa caché si no hay código guardado (caso TRIAL)"""
        codigo = self.gestor_licencias.obtener_codigo_guardado()

        if not codigo:
            # Sin código — lanzar wizard automáticamente
            import subprocess
            if getattr(sys, 'frozen', False):
                wizard = os.path.join(os.path.dirname(sys.executable), "WizardMensajes.exe")
            else:
                wizard = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wizard_primera_vez.py")
            if os.path.exists(wizard):
                subprocess.Popen([wizard])
            else:
                messagebox.showwarning("Sin Licencia", "No hay licencia configurada.\n\nEjecuta el Wizard de primera vez.")
            return None

        resultado = self.gestor_licencias.verificar_licencia(codigo, mostrar_mensajes=False)

        if not resultado['valida']:
            messagebox.showerror("Licencia Inválida", "Tu licencia no es válida o ha expirado.")
            return None

        # Verificar expiración para licencias TRIAL
        tipo = resultado.get('tipo', 'TRIAL')
        if tipo == 'TRIAL':
            dias = resultado.get('diasRestantes', 0)
            if dias is not None and dias <= 0:
                messagebox.showwarning(
                    "⏰ Período de Prueba Expirado",
                    "Tu período de prueba ha terminado.\n\n"
                    "Adquiere la versión Completa para seguir usando todas las funciones.\n\n"
                    "Visita: automapro-frontend.vercel.app"
                )
                self._abrir_upgrade()
                return None

        return resultado

    def _verificar_actualizacion(self):
        """Verifica si hay una versión nueva disponible en segundo plano"""
        import threading
        def consultar():
            try:
                import sys, os
                base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                with open(os.path.join(base, 'version.txt'), 'r') as f:
                    version_local = f.read().strip()
            except Exception:
                version_local = "1.0.0"
            resultado = self.gestor_licencias.verificar_actualizacion(version_local)
            if resultado.get('hay_actualizacion'):
                version_nueva = resultado.get('version_nueva')
                ruta_archivo = resultado.get('ruta_archivo', '')
                self.root.after(0, lambda: self._mostrar_ventana_actualizacion(version_local, version_nueva, ruta_archivo))
        threading.Thread(target=consultar, daemon=True).start()

    def _mostrar_ventana_actualizacion(self, version_local, version_nueva, ruta_archivo):
        """Muestra ventana modal de actualización disponible"""
        import tkinter as tk
        from tkinter import ttk
        import urllib.request
        import subprocess
        import tempfile
        import os
        import threading

        ventana = tk.Toplevel(self.root)
        ventana.title("Actualización Disponible")
        ventana.resizable(False, False)
        ventana.configure(bg="#f0f0f0")
        ventana.grab_set()

        # Centrar ventana
        ventana.withdraw()
        ventana.update_idletasks()
        w, h = 420, 280
        x = (ventana.winfo_screenwidth() // 2) - (w // 2)
        y = (ventana.winfo_screenheight() // 2) - (h // 2)
        ventana.geometry(f"{w}x{h}+{x}+{y}")
        ventana.deiconify()

        # Header
        header = tk.Frame(ventana, bg="#1a73e8", pady=15)
        header.pack(fill='x')
        tk.Label(
            header,
            text="🔄  Actualización Disponible",
            font=("Segoe UI", 13, "bold"),
            bg="#1a73e8",
            fg="white"
        ).pack()

        # Cuerpo
        cuerpo = tk.Frame(ventana, bg="#f0f0f0", padx=30, pady=15)
        cuerpo.pack(fill='both', expand=True)

        tk.Label(cuerpo, text=f"Versión actual:      {version_local}", font=("Segoe UI", 10), bg="#f0f0f0", anchor='w').pack(fill='x')
        tk.Label(cuerpo, text=f"Nueva versión:       {version_nueva}", font=("Segoe UI", 10, "bold"), bg="#f0f0f0", fg="#1a73e8", anchor='w').pack(fill='x', pady=(0, 10))
        tk.Label(
            cuerpo,
            text="Hay una nueva versión disponible.\nHaz clic en Actualizar para instalarla automáticamente.",
            font=("Segoe UI", 9),
            bg="#f0f0f0",
            fg="#555555",
            justify='left'
        ).pack(fill='x')

        # Barra de progreso (oculta inicialmente)
        progreso_frame = tk.Frame(ventana, bg="#f0f0f0", padx=30)
        progreso_frame.pack(fill='x')
        label_progreso = tk.Label(progreso_frame, text="", font=("Segoe UI", 9), bg="#f0f0f0", fg="#555555")
        label_progreso.pack(anchor='w')
        barra = ttk.Progressbar(progreso_frame, mode='indeterminate', length=360)

        # Botones
        frame_btns = tk.Frame(ventana, bg="#f0f0f0", pady=10)
        frame_btns.pack(fill='x', padx=30)

        def recordar_despues():
            ventana.grab_release()
            ventana.destroy()

        def actualizar_ahora():
            if not ruta_archivo:
                recordar_despues()
                return

            btn_actualizar.config(state='disabled')
            btn_despues.config(state='disabled')
            label_progreso.config(text="Descargando actualización...")
            barra.pack(fill='x', pady=5)
            barra.start(10)
            ventana.update()

            def descargar_e_instalar():
                try:
                    tmp = tempfile.mktemp(suffix=".exe")
                    urllib.request.urlretrieve(ruta_archivo, tmp)

                    self.root.after(0, lambda: label_progreso.config(text="Instalando..."))
                    self.root.after(500, lambda: _ejecutar_instalador(tmp))
                except Exception as e:
                    self.root.after(0, lambda: label_progreso.config(text=f"Error: {e}"))
                    self.root.after(0, lambda: barra.stop())

            def _ejecutar_instalador(ruta_tmp):
                barra.stop()
                ventana.grab_release()
                ventana.destroy()
                self.root.destroy()
                subprocess.Popen([ruta_tmp, '/SILENT'])

            threading.Thread(target=descargar_e_instalar, daemon=True).start()

        btn_despues = tk.Button(
            frame_btns,
            text="Recordar después",
            font=("Segoe UI", 10),
            bg="#e0e0e0",
            width=16,
            command=recordar_despues
        )
        btn_despues.pack(side='left')

        btn_actualizar = tk.Button(
            frame_btns,
            text="Actualizar ahora",
            font=("Segoe UI", 10, "bold"),
            bg="#1a73e8",
            fg="white",
            width=16,
            command=actualizar_ahora
        )
        btn_actualizar.pack(side='right')

    def _construir_ui(self):
        """Construye la interfaz del panel"""
        tipo_licencia = self.licencia.get('tipo', 'TRIAL')
        es_full = tipo_licencia in ['FULL', 'MASTER'] or self.licencia.get('developer_permanente')

        # ==================== HEADER ====================
        header = tk.Frame(self.root, bg="#1a73e8", pady=15)
        header.pack(fill='x')

        # Leer versión desde version.txt
        try:
            ruta_version = os.path.join(self.base_dir, 'version.txt')
            with open(ruta_version, 'r', encoding='utf-8') as f:
                version = f.read().strip()
        except Exception:
            version = '1.0.0'

        tk.Label(
            header,
            text="📘 Mensajes Bíblicos",
            font=("Segoe UI", 20, "bold"),
            bg="#1a73e8",
            fg="white"
        ).pack()

        tk.Label(
            header,
            text=f"v{version}",
            font=("Segoe UI", 9),
            bg="#1a73e8",
            fg="#c8d8f8"
        ).pack()

        # Badge de licencia
        if self.licencia.get('developer_permanente'):
            texto_lic = "👑 LICENCIA MAESTRA"
            color_lic = "#6f42c1"
        elif tipo_licencia == "FULL":
            texto_lic = "✅ LICENCIA COMPLETA"
            color_lic = "#28a745"
        else:
            dias = self.licencia.get('diasRestantes', 0)
            texto_lic = f"⚠️  PRUEBA — {dias} días restantes"
            color_lic = "#e65100"

        tk.Label(
            header,
            text=texto_lic,
            font=("Segoe UI", 10, "bold"),
            bg=color_lic,
            fg="white",
            padx=15,
            pady=4
        ).pack(pady=(8, 0))

        # Banner upgrade (solo TRIAL)
        if not es_full:
            banner = tk.Frame(self.root, bg="#fff3cd", pady=8)
            banner.pack(fill='x')
            tk.Label(
                banner,
                text="🔓 Desbloquea WhatsApp, tareas automáticas y más con la versión Completa",
                font=("Segoe UI", 9),
                bg="#fff3cd",
                fg="#856404"
            ).pack(side='left', padx=(15, 10))
            tk.Button(
                banner,
                text="⬆️ Comprar versión Completa",
                font=("Segoe UI", 9, "bold"),
                bg="#ffc107",
                fg="#212529",
                cursor="hand2",
                relief='flat',
                padx=10,
                command=self._abrir_upgrade
            ).pack(side='right', padx=(0, 15))

        # ==================== GRID PRINCIPAL ====================
        container = tk.Frame(self.root, bg="#f0f0f0")
        container.pack(fill='both', expand=True, padx=25, pady=15)

        grid = tk.Frame(container, bg="#f0f0f0")
        grid.pack(fill='both', expand=True)

        self._botones_grid = []  # Para bloquear/desbloquear todos juntos

        # Fila 0
        self._boton(grid, "⚡\nAcciones", "Publicar y automatizar",
                    self._abrir_acciones, row=0, col=0, color="#e65100")
        self._boton(grid, "⚙️\nConfigurador", "Ajustar configuración",
                    self._abrir_configurador, row=0, col=1, en_hilo=True)

        # Fila 1
        if es_full:
            self._boton(grid, "📝\nMensajes", "Crear y editar mensajes",
                        self._abrir_gestor_mensajes, row=1, col=0, en_hilo=True)
        else:
            self._boton(grid, "📝\nMensajes", "Ver tus mensajes",
                        self._abrir_carpeta_mensajes, row=1, col=0)
        self._boton(grid, "📊\nEstadísticas", "Ver historial",
                    self._ver_estadisticas, row=1, col=1)

        # Fila 2
        if es_full:
            self._boton(grid, "🗓️\nTareas Automáticas", "Programar publicaciones",
                        self._gestionar_tareas, row=2, col=0, color="#28a745", en_hilo=True)
        else:
            self._boton(grid, "🔒\nTareas Automáticas", "Solo versión Completa",
                        self._mostrar_mensaje_upgrade, row=2, col=0, color="#9e9e9e")

        self._boton(grid, "❓\nAyuda", "Cómo usar el sistema",
                    self._mostrar_ayuda, row=2, col=1)

        # Fila 3
        self._boton(grid, "❌\nSalir", "Cerrar panel",
                    self.root.destroy, row=3, col=0, color="#dc3545")

    def _bloquear_grid(self):
        """Bloquea todos los botones del grid"""
        self.root.config(cursor="wait")
        for frame, widgets in self._botones_grid:
            frame.config(cursor="", bg="#e0e0e0")
            for w in widgets:
                w.config(bg="#e0e0e0")
                w.unbind('<Button-1>')
                w.unbind('<Enter>')
                w.unbind('<Leave>')
            frame.unbind('<Button-1>')
            frame.unbind('<Enter>')
            frame.unbind('<Leave>')

    def _desbloquear_grid(self):
        """Restaura todos los botones del grid"""
        self.root.config(cursor="")
        for frame, widgets in self._botones_grid:
            frame.config(cursor="hand2", bg="white")
            cmd = frame._cmd
            en_hilo = frame._en_hilo
            for w in widgets:
                w.config(bg="white")
                accion = (lambda c=cmd: self._lanzar_en_hilo(c)) if en_hilo else cmd
                w.bind('<Button-1>', lambda e, a=accion: a())
                w.bind('<Enter>', lambda e, f=frame: f.config(bg="#f8f9fa"))
                w.bind('<Leave>', lambda e, f=frame: f.config(bg="white"))
            accion = (lambda c=cmd: self._lanzar_en_hilo(c)) if en_hilo else cmd
            frame.bind('<Button-1>', lambda e, a=accion: a())
            frame.bind('<Enter>', lambda e, f=frame: f.config(bg="#f8f9fa"))
            frame.bind('<Leave>', lambda e, f=frame: f.config(bg="white"))

    def _lanzar_accion(self, cmd):
        """Para acciones que abren ventanas: bloquea grid brevemente para evitar doble clic"""
        self._bloquear_grid()
        self.root.after(300, self._desbloquear_grid)
        cmd()

    def _lanzar_subprocess(self, cmd):
        """Para subprocesos externos: bloquea grid, espera cierre del proceso, desbloquea"""
        self._bloquear_grid()
        import threading
        def _hilo():
            try:
                cmd()
            finally:
                pass  # El cmd maneja su propio desbloqueo
        threading.Thread(target=_hilo, daemon=True).start()

    def _lanzar_en_hilo(self, cmd):
        """Para subprocesos: bloquea grid, corre en hilo, desbloquea al terminar"""
        self._bloquear_grid()
        import threading
        def _hilo():
            try:
                cmd()
            finally:
                self.root.after(0, self._desbloquear_grid)
        threading.Thread(target=_hilo, daemon=True).start()

    def _centrar_ventana(self, ventana, ancho, alto):
        """Centra una ventana en pantalla antes de mostrarla"""
        x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
        y = (ventana.winfo_screenheight() // 2) - (alto // 2)
        ventana.geometry(f'{ancho}x{alto}+{x}+{y}')

    def _boton(self, parent, texto, subtexto, comando, row, col, color="#1a73e8", en_hilo=False):
        """Crea un botón estilizado en el grid"""
        frame = tk.Frame(parent, bg="white", relief='solid', borderwidth=1, cursor="hand2")
        frame.grid(row=row, column=col, padx=8, pady=8, sticky='nsew')
        parent.grid_rowconfigure(row, weight=1)
        parent.grid_columnconfigure(col, weight=1)
        frame._cmd = comando
        frame._en_hilo = en_hilo

        lbl1 = tk.Label(frame, text=texto, font=("Segoe UI", 13, "bold"), bg="white", fg=color)
        lbl1.pack(expand=True, pady=(12, 3))

        lbl2 = tk.Label(frame, text=subtexto, font=("Segoe UI", 8), bg="white", fg="gray")
        lbl2.pack(expand=True, pady=(0, 12))

        if en_hilo:
            accion = lambda c=comando: self._lanzar_en_hilo(c)
        else:
            accion = lambda c=comando: self._lanzar_accion(c)
        for w in [frame, lbl1, lbl2]:
            w.bind('<Button-1>', lambda e, a=accion: a())
            w.bind('<Enter>', lambda e, f=frame: f.config(bg="#f8f9fa"))
            w.bind('<Leave>', lambda e, f=frame: f.config(bg="white"))

        self._botones_grid.append((frame, [lbl1, lbl2]))

    # ==================== VENTANA ACCIONES ====================

    def _abrir_acciones(self):
        """Abre ventana de acciones disponibles según licencia"""
        tipo_licencia = self.licencia.get('tipo', 'TRIAL')
        es_full = tipo_licencia in ['FULL', 'MASTER'] or self.licencia.get('developer_permanente')

        ventana = tk.Toplevel(self.root)
        ventana.withdraw()
        ventana.title("⚡ Acciones")
        ventana.resizable(False, False)
        ventana.configure(bg="#f0f0f0")
        ventana.transient(self.root)
        ventana.grab_set()

        # Header
        header = tk.Frame(ventana, bg="#e65100", pady=12)
        header.pack(fill='x')
        tk.Label(
            header,
            text="⚡ Acciones",
            font=("Segoe UI", 14, "bold"),
            bg="#e65100",
            fg="white"
        ).pack()
        tk.Label(
            header,
            text="Selecciona qué deseas ejecutar",
            font=("Segoe UI", 9),
            bg="#e65100",
            fg="white"
        ).pack()

        frame = tk.Frame(ventana, bg="#f0f0f0")
        frame.pack(fill='both', expand=True, padx=20, pady=15)

        # Verificar predicaciones pendientes desde archivo de estado
        from compartido.gestor_archivos import leer_estado_predicaciones
        estado = leer_estado_predicaciones()
        hay_predicaciones = estado.get('pendientes', 0) > 0

        # Acción 1 — siempre disponible
        tk.Button(
            frame,
            text="▶️  Publicar Mensaje Bíblico en Facebook",
            font=("Segoe UI", 11, "bold"),
            bg="#1a73e8",
            fg="white",
            activebackground="#155ab6",
            cursor="hand2",
            anchor='w',
            padx=15,
            pady=8,
            command=lambda: [ventana.destroy(), self._publicar_facebook()]
        ).pack(fill='x', pady=(0, 8))

        # Acción 2 — Enviar Oraciones por WhatsApp
        tk.Button(
            frame,
            text="📱  Enviar Oraciones por WhatsApp" if es_full else "🔒  Enviar Oraciones por WhatsApp  —  versión Completa",
            font=("Segoe UI", 11, "bold") if es_full else ("Segoe UI", 11),
            bg="#25D366" if es_full else "#e0e0e0",
            fg="white" if es_full else "#9e9e9e",
            cursor="hand2",
            anchor='w',
            padx=15,
            pady=8,
            command=lambda: [ventana.destroy(), self._enviar_oraciones()] if es_full else self._mostrar_mensaje_upgrade()
        ).pack(fill='x', pady=(0, 8))

        # Acción 3 — Extraer Predicaciones
        tk.Button(
            frame,
            text="🎬  Extraer Predicaciones" if es_full else "🔒  Extraer Predicaciones  —  versión Completa",
            font=("Segoe UI", 11, "bold") if es_full else ("Segoe UI", 11),
            bg="#25D366" if es_full else "#e0e0e0",
            fg="white" if es_full else "#9e9e9e",
            cursor="hand2",
            anchor='w',
            padx=15,
            pady=8,
            command=lambda: [ventana.destroy(), self._extraer_predicaciones()] if es_full else self._mostrar_mensaje_upgrade()
        ).pack(fill='x', pady=(0, 8))

        # Acción 4 — Publicar Predicaciones en Facebook
        if es_full:
            color_pred = "#1a73e8" if hay_predicaciones else "#90a4ae"
            cmd_pred = (lambda: [ventana.destroy(), self._publicar_predicaciones()]) \
                       if hay_predicaciones else self._sin_predicaciones
            texto_pred = "📤  Publicar Prédica Extraída" if hay_predicaciones else "📭  Sin prédicas extraídas"
        else:
            color_pred = "#e0e0e0"
            cmd_pred = self._mostrar_mensaje_upgrade
            texto_pred = "🔒  Publicar Prédica Extraída  —  versión Completa"
        tk.Button(
            frame,
            text=texto_pred,
            font=("Segoe UI", 11, "bold") if es_full else ("Segoe UI", 11),
            bg=color_pred,
            fg="white" if es_full else "#9e9e9e",
            cursor="hand2",
            anchor='w',
            padx=15,
            pady=8,
            command=cmd_pred
        ).pack(fill='x', pady=(0, 8))

        # Acción 5 — Enviar Mensaje por Correo
        tk.Button(
            frame,
            text="✉️  Enviar Mensaje por Correo" if es_full else "🔒  Enviar Mensaje por Correo  —  versión Completa",
            font=("Segoe UI", 11, "bold") if es_full else ("Segoe UI", 11),
            bg="#6f42c1" if es_full else "#e0e0e0",
            fg="white" if es_full else "#9e9e9e",
            cursor="hand2",
            anchor='w',
            padx=15,
            pady=8,
            command=lambda: [ventana.destroy(), self._enviar_correo()] if es_full else self._mostrar_mensaje_upgrade()
        ).pack(fill='x', pady=(0, 8))

        # Acción 6 — Ejecutar Secuencia Configurada
        if es_full:
            tk.Button(
                frame,
                text="⚡  Ejecutar Secuencia Configurada",
                font=("Segoe UI", 11, "bold"),
                bg="#e65100",
                fg="white",
                activebackground="#bf360c",
                cursor="hand2",
                anchor='w',
                padx=15,
                pady=8,
                command=lambda: [ventana.destroy(), self._ejecutar_secuencia()]
            ).pack(fill='x', pady=(0, 8))
        else:
            tk.Button(
                frame,
                text="🔒  Ejecutar Secuencia Configurada  —  versión Completa",
                font=("Segoe UI", 11),
                bg="#e0e0e0",
                fg="#9e9e9e",
                cursor="hand2",
                anchor='w',
                padx=15,
                pady=8,
                command=self._mostrar_mensaje_upgrade
            ).pack(fill='x', pady=(0, 8))

        tk.Button(
            frame,
            text="Cerrar",
            font=("Segoe UI", 10),
            bg="#6c757d",
            fg="white",
            width=12,
            command=ventana.destroy
        ).pack(pady=15)

        self._centrar_ventana(ventana, 500, 525)
        ventana.deiconify()

    # ==================== ACCIONES ====================

    def _ejecutar_secuencia(self):
        """Ejecuta los módulos en el orden configurado en Secuencia"""
        import configparser
        cfg = configparser.ConfigParser()
        cfg.read(os.path.join(self.base_dir, "config_global.txt"), encoding='utf-8')
        modulos = cfg.get('SECUENCIA', 'modulos_activos', fallback='').strip()

        if not modulos:
            respuesta = messagebox.askyesno(
                "⚙️ Secuencia no configurada",
                "No has configurado la secuencia de módulos.\n\n"
                "¿Deseas ir al Configurador para definirla ahora?"
            )
            if respuesta:
                self._abrir_configurador(pestana='secuencia')
                return
            # Si dice No → ejecutar con módulo por defecto
            try:
                exe = self._exe("MensajesBiblicos.exe")
                if os.path.exists(exe):
                    subprocess.Popen([exe, "--secuencia"]).wait()
                self._toast("⚡ Secuencia completada", "Módulo bíblico ejecutado")
            except Exception as e:
                messagebox.showerror("❌ Error en secuencia", f"Error ejecutando la secuencia:\n{e}")
            return

        lista = [m.strip() for m in modulos.split(',') if m.strip()]

        # Validar configuración antes de ejecutar
        if 'extraer' in lista:
            problema = problema_fuentes_predicaciones()
            if problema:
                respuesta = messagebox.askyesno(
                    "⚠️ Configuración incompleta",
                    f"La secuencia incluye 'Extraer Predicaciones':\n{problema}.\n\n"
                    "¿Deseas ir al Configurador para completarlo ahora?"
                )
                if respuesta:
                    self._abrir_configurador(pestana='extractor')
                return

        try:
            exe = self._exe("MensajesBiblicos.exe")
            if os.path.exists(exe):
                subprocess.Popen([exe, "--secuencia"]).wait()
            else:
                subprocess.Popen([sys.executable, "publicar_facebook.py", "--secuencia"]).wait()
            self._toast("⚡ Secuencia completada", "Todos los módulos ejecutados")
        except Exception as e:
            messagebox.showerror("❌ Error en secuencia", f"Error ejecutando la secuencia:\n{e}")

    def _publicar_facebook(self):
        try:
            exe = self._exe("MensajesBiblicos.exe")
            if os.path.exists(exe):
                subprocess.Popen([exe, "--solo-biblico"])
            else:
                subprocess.Popen([sys.executable, "flujo_completo_facebook.py", "--solo-biblico"])
            self._toast("🚀 Publicación iniciada", "El navegador se abrirá en unos segundos...")
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo iniciar la publicación:\n{e}")

    def _enviar_correo(self):
        from publicadores.publicador_correo import falta_configuracion_correo
        problema = falta_configuracion_correo()
        if problema:
            if messagebox.askyesno("⚠️ Correo sin configurar",
                                   f"{problema}.\n\n¿Deseas abrir el Configurador para completarlo ahora?"):
                self._abrir_configurador(pestana='correo')
            return
        try:
            exe = self._exe("MensajesBiblicos.exe")
            if os.path.exists(exe):
                subprocess.Popen([exe, "--modulo", "correo"])
            else:
                subprocess.Popen([sys.executable, "publicar_facebook.py", "--modulo", "correo"])
            self._toast("✉️ Envío iniciado", "Se enviará el mensaje a tus destinatarios de correo")
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo iniciar el envío:\n{e}")

    def _enviar_oraciones(self):
        """Abre la selección de destinatarios para este envío de oraciones"""
        import json

        archivo_grupos = os.path.join(self.base_dir, "llamados-oracion", "grupos.json")

        if not os.path.exists(archivo_grupos):
            respuesta = messagebox.askyesno(
                "⚠️ Sin grupos configurados",
                "No hay grupos de oración configurados.\n\n"
                "¿Deseas abrir el Configurador para agregarlos ahora?"
            )
            if respuesta:
                self._abrir_configurador(pestaña='oraciones')
            return

        try:
            with open(archivo_grupos, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            grupos = [g for g in datos.get('grupos', []) if g.get('activo', True)]
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error leyendo grupos:\n{e}")
            return

        if not grupos:
            respuesta = messagebox.askokcancel(
                "⚠️ Sin grupos ni contactos",
                "No hay grupos ni contactos registrados para oraciones.\n\n"
                "¿Deseas abrir el Configurador para agregarlos ahora?"
            )
            if respuesta:
                self._abrir_configurador(pestaña='oraciones')
            return

        self._abrir_selector_oraciones(archivo_grupos, grupos)

    def _nombre_corto(self, nombre, maximo=17):
        """Acorta nombres largos solo para mostrarlos; el nombre completo se usa al enviar"""
        return nombre if len(nombre) <= maximo else nombre[:maximo].rstrip() + "…"

    def _leer_mensajes_oracion(self):
        """Retorna (mensajes_grupos, mensajes_individuales) desde mensajes_oracion.txt"""
        archivo_msg = os.path.join(self.base_dir, "llamados-oracion", "mensajes_oracion.txt")
        if not os.path.exists(archivo_msg):
            return [], []

        with open(archivo_msg, 'r', encoding='utf-8') as f:
            contenido = f.read()

        if '[GRUPOS]' in contenido and '[INDIVIDUALES]' in contenido:
            partes = contenido.split('[INDIVIDUALES]')
            mensajes_grupos = [l.strip() for l in partes[0].replace('[GRUPOS]', '').strip().split('\n') if l.strip()]
            mensajes_individuales = [l.strip() for l in partes[1].strip().split('\n') if l.strip()]
            return mensajes_grupos, mensajes_individuales

        todas = [l.strip() for l in contenido.split('\n') if l.strip() and not l.startswith('[')]
        return todas, todas

    def _abrir_selector_oraciones(self, archivo_grupos, grupos):
        """Ventana para elegir los destinatarios de este envío sin cambiar los de por defecto"""
        import json
        from tkinter import ttk

        ventana = tk.Toplevel(self.root)
        ventana.withdraw()
        ventana.title("📱 Enviar oraciones")
        ventana.resizable(False, False)
        ventana.configure(bg="#f0f0f0")
        ventana.transient(self.root)
        ventana.grab_set()

        def cerrar():
            ventana.grab_release()
            ventana.destroy()

        header = tk.Frame(ventana, bg="#25D366", pady=12)
        header.pack(fill='x')
        tk.Label(header, text="📱 Enviar oraciones por WhatsApp",
                 font=("Segoe UI", 12, "bold"), bg="#25D366", fg="white").pack()
        tk.Label(header, text="Elige quién recibe la oración en este envío",
                 font=("Segoe UI", 8), bg="#25D366", fg="#eafff1").pack()

        frame = tk.Frame(ventana, bg="#f0f0f0", padx=20, pady=10)
        frame.pack(fill='both', expand=True)

        vars_sel = []
        vars_msg = []
        var_todos = tk.BooleanVar()

        def toggle_todos():
            for v in vars_sel:
                v.set(var_todos.get())

        tk.Checkbutton(frame, text="Seleccionar todos", variable=var_todos, command=toggle_todos,
                       font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', pady=(0, 4))
        tk.Frame(frame, bg="#ccc", height=1).pack(fill='x', pady=(0, 8))

        canvas = tk.Canvas(frame, bg="#f0f0f0", highlightthickness=0, height=200)
        scroll = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
        frame_scroll = tk.Frame(canvas, bg="#f0f0f0")
        frame_scroll.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=frame_scroll, anchor='nw')
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        mensajes_grupos, mensajes_individuales = self._leer_mensajes_oracion()

        for g in grupos:
            var = tk.BooleanVar(value=g.get('seleccionado', True))
            vars_sel.append(var)

            disponibles = mensajes_grupos if g.get('tipo') == 'grupo' else mensajes_individuales
            guardado = g.get('mensaje_asignado')
            var_msg = tk.StringVar(value=guardado if guardado in disponibles else "🎲 Aleatorio")
            vars_msg.append(var_msg)

            fila = tk.Frame(frame_scroll, bg="#f0f0f0")
            fila.pack(fill='x', pady=3)
            icono = "👥" if g.get('tipo') == 'grupo' else "👤"
            tk.Checkbutton(fila, text=f"{icono} {self._nombre_corto(g['nombre'])}", variable=var, bg="#f0f0f0",
                           font=("Segoe UI", 10), width=20, anchor='w').pack(side='left')
            ttk.Combobox(fila, textvariable=var_msg, values=["🎲 Aleatorio"] + disponibles,
                         state='readonly', width=30, font=("Segoe UI", 8)).pack(side='left', padx=(5, 0))

        def actualizar_todos(*_):
            var_todos.set(all(v.get() for v in vars_sel))
        for v in vars_sel:
            v.trace_add('write', actualizar_todos)
        actualizar_todos()

        var_guardar = tk.BooleanVar(value=False)
        tk.Checkbutton(ventana, text="💾 Guardar también como destinatarios por defecto", variable=var_guardar,
                       font=("Segoe UI", 9), bg="#f0f0f0").pack(anchor='w', padx=20, pady=(4, 0))

        def enviar():
            estado = {}
            elegidos = []
            for g, var, var_msg in zip(grupos, vars_sel, vars_msg):
                mensaje = None if var_msg.get() == "🎲 Aleatorio" else var_msg.get()
                estado[g['nombre']] = (var.get(), mensaje)
                if var.get():
                    elegidos.append({
                        'nombre': g['nombre'],
                        'tipo': g.get('tipo', 'grupo'),
                        'mensaje_asignado': mensaje
                    })

            if not elegidos:
                messagebox.showwarning("⚠️ Aviso", "Marca al menos un destinatario", parent=ventana)
                return

            ruta = os.path.join(self.base_dir, "destinatarios_ejecucion.json")
            try:
                if var_guardar.get():
                    with open(archivo_grupos, 'r', encoding='utf-8') as f:
                        datos = json.load(f)
                    for g in datos.get('grupos', []):
                        if g.get('nombre') in estado:
                            g['seleccionado'], g['mensaje_asignado'] = estado[g['nombre']]
                    with open(archivo_grupos, 'w', encoding='utf-8') as f:
                        json.dump(datos, f, ensure_ascii=False, indent=2)

                with open(ruta, 'w', encoding='utf-8') as f:
                    json.dump({'grupos': elegidos}, f, ensure_ascii=False, indent=2)
            except Exception as e:
                messagebox.showerror("❌ Error", f"Error guardando la selección:\n{e}", parent=ventana)
                return

            cerrar()
            try:
                exe = self._exe("OracionesWhatsApp.exe")
                if os.path.exists(exe):
                    subprocess.Popen([exe, "--destinatarios", ruta])
                else:
                    script = os.path.join(self.base_dir, "publicadores", "whatsapp_oracion.py")
                    subprocess.Popen([sys.executable, script, "--destinatarios", ruta])
                self._toast("📱 Oraciones WhatsApp", f"Enviando a {len(elegidos)} destinatario(s)...")
            except Exception as e:
                messagebox.showerror("❌ Error", f"No se pudo iniciar el módulo:\n{e}")

        frame_footer = tk.Frame(ventana, bg="#f0f0f0", padx=20)
        frame_footer.pack(fill='x', pady=(8, 15))
        tk.Button(frame_footer, text="Cancelar", font=("Segoe UI", 10),
                  bg="#e0e0e0", command=cerrar, width=12).pack(side='left')
        tk.Button(frame_footer, text="📱 Enviar", font=("Segoe UI", 10, "bold"),
                  bg="#25D366", fg="white", command=enviar, width=14).pack(side='right')

        ventana.protocol("WM_DELETE_WINDOW", cerrar)
        ventana.update_idletasks()
        self._centrar_ventana(ventana, 500, 440)
        ventana.deiconify()

    def _abrir_configurador(self, pestaña=None, pestana=None):
        """Abre el configurador — bloquea el grid mientras está abierto"""
        try:
            exe = self._exe("ConfiguradorMensajes.exe")
            pestana_final = pestaña or pestana
            args = [exe] if os.path.exists(exe) else [sys.executable, "configurador_gui.py"]
            if pestana_final:
                args.append(f"--pestana={pestana_final}")
            subprocess.run(args)
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo abrir el configurador:\n{e}")

    def _extraer_predicaciones(self):
        # Verificar las fuentes (grupo de WhatsApp y/o carpeta) antes de lanzar el exe
        problema = problema_fuentes_predicaciones()
        if problema:
            respuesta = messagebox.askokcancel(
                "⚠️ Extractor sin configurar",
                f"{problema}.\n\n"
                "¿Deseas abrir el Configurador para completarlo ahora?"
            )
            if respuesta:
                self._abrir_configurador(pestaña='extractor')
            return
        else:
            self._lanzar_extractor()

    def _lanzar_extractor(self):
        try:
            exe = self._exe("ExtractorPredicaciones.exe")
            if os.path.exists(exe):
                subprocess.Popen([exe])
            else:
                subprocess.Popen([sys.executable, "extraer_predicaciones_whatsapp.py"])
            self._toast("🎬 Extrayendo predicaciones", "Buscando prédicas nuevas...")
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo iniciar el módulo:\n{e}")

    def _publicar_predicaciones(self):
        try:
            exe = self._exe("MensajesBiblicos.exe")
            if os.path.exists(exe):
                subprocess.Popen([exe, "--modulo", "publicar_predicaciones"])
            else:
                subprocess.Popen([sys.executable, "flujo_completo_facebook.py",
                                  "--solo-predicaciones"])
            self._toast("📤 Publicando predicaciones", "Publicando en Facebook...")
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo publicar:\n{e}")

    def _sin_predicaciones(self):
        messagebox.showinfo(
            "Sin predicaciones",
            "No hay predicaciones extraídas.\n\n"
            "Primero usa 'Extraer Predicaciones'\n"
            "y luego podrás publicarlas en Facebook."
        )

    def _abrir_carpeta_mensajes(self):
        """TRIAL: abre la carpeta mensajes en el explorador e informa sobre el gestor"""
        import subprocess as sp
        carpeta = os.path.join(os.path.dirname(self._exe("MensajesBiblicos.exe")), "mensajes")
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)
        sp.Popen(f'explorer "{carpeta}"')
        self._toast(
            "📝 Tus Mensajes",
            "Carpeta abierta — version Completa incluye editor visual",
            duracion=5000
        )

    def _abrir_gestor_mensajes(self):
        try:
            exe = self._exe("GestorMensajes.exe")
            if os.path.exists(exe):
                subprocess.run([exe])
            else:
                subprocess.run([sys.executable, "gestor_mensajes_gui.py"])
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo abrir el gestor:\n{e}")

    def _gestionar_tareas(self):
        try:
            exe = self._exe("GestorTareasMensajes.exe")
            if os.path.exists(exe):
                subprocess.run([exe])
            else:
                messagebox.showerror("❌ Error", "No se encontró GestorTareasMensajes.exe")
        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo abrir el gestor de tareas:\n{e}")

    def _abrir_upgrade(self):
        """Abre la página de compra con el código de licencia del usuario"""
        import webbrowser
        try:
            codigo = self.gestor_licencias.obtener_codigo_guardado()
            url = f"https://automapro-frontend.vercel.app/cliente/comprar?codigo={codigo}&app=1"
            webbrowser.open(url)
        except Exception:
            webbrowser.open("https://automapro-frontend.vercel.app/catalogo")

    def _mostrar_mensaje_upgrade(self):
        """Muestra mensaje cuando el usuario intenta acceder a función premium"""
        messagebox.showinfo(
            "🔒 Función Premium",
            "Esta función está disponible solo en la versión Completa.\n\n"
            "Adquiérela en automapro.com para desbloquear:\n"
            "• Enviar Oraciones por WhatsApp\n"
            "• Extraer Predicaciones\n"
            "• Publicar Predicaciones en Facebook\n"
            "• Tareas Automáticas"
        )

    def _ver_estadisticas(self):
        """Muestra ventana de estadísticas"""
        try:
            gestor = GestorRegistro()
            stats = gestor.obtener_estadisticas()
            fecha_ultima = stats.get('ultima_publicacion') or 'Nunca'

            ventana = tk.Toplevel(self.root)
            ventana.withdraw()
            ventana.title("📊 Estadísticas")
            ventana.resizable(False, False)
            ventana.configure(bg="#f0f0f0")
            ventana.transient(self.root)
            ventana.grab_set()

            header = tk.Frame(ventana, bg="#1a73e8", pady=12)
            header.pack(fill='x')
            tk.Label(header, text="📊 Estadísticas del Sistema",
                     font=("Segoe UI", 13, "bold"), bg="#1a73e8", fg="white").pack()

            frame = tk.Frame(ventana, bg="white", padx=25, pady=15)
            frame.pack(fill='both', expand=True, padx=15, pady=15)

            items = [
                ("📈 Total publicaciones:", str(stats.get('total_publicaciones', 0))),
                ("✅ Exitosas:", str(stats.get('publicaciones_exitosas', 0))),
                ("❌ Fallidas:", str(stats.get('publicaciones_fallidas', 0))),
                ("🎯 Tasa de éxito:", f"{stats.get('tasa_exito', 0):.1f}%"),
                ("⏱️ Tiempo promedio:", f"{stats.get('tiempo_promedio', 0):.1f}s"),
                ("📅 Última publicación:", fecha_ultima),
            ]

            for label, valor in items:
                row = tk.Frame(frame, bg="white")
                row.pack(fill='x', pady=5)
                tk.Label(row, text=label, font=("Segoe UI", 10, "bold"),
                         bg="white", anchor='w', width=25).pack(side='left')
                tk.Label(row, text=valor, font=("Segoe UI", 10),
                         bg="white", anchor='w').pack(side='left')

            tk.Button(
                ventana,
                text="Cerrar",
                font=("Segoe UI", 10),
                bg="#6c757d",
                fg="white",
                width=12,
                command=ventana.destroy
            ).pack(pady=15)

            self._centrar_ventana(ventana, 470, 370)
            ventana.deiconify()

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error mostrando estadísticas:\n{e}")

    def _mostrar_ayuda(self):
        ventana = tk.Toplevel(self.root)
        ventana.withdraw()
        ventana.title("❓ Centro de Ayuda")
        ventana.resizable(False, False)
        ventana.configure(bg="#f0f0f0")
        ventana.transient(self.root)
        ventana.grab_set()

        TEMAS = [
            ("▶️  Publicar Mensaje Bíblico",
             "▶️ PUBLICAR MENSAJE BÍBLICO EN FACEBOOK\n\n"
             "Publica automáticamente mensajes bíblicos en tu perfil de Facebook.\n\n"
             "¿Qué hace?\n"
             "• Abre el navegador configurado (Firefox, Chrome o Edge) con su propia ventana de consola\n"
             "• Usa tu sesión de Facebook guardada (aunque tengas ese navegador abierto)\n"
             "• Elige los mensajes de tu carpeta 'mensajes' según el modo configurado\n"
             "• Publica la cantidad configurada (1 por defecto), esperando el tiempo mínimo entre cada uno\n"
             "• Los enlaces (https://...) salen clicables y con vista previa\n"
             "• Registra cada publicación en las Estadísticas\n\n"
             "Modos de selección:\n"
             "• 🎲 Aleatorio → evita repetir los últimos publicados\n"
             "• 📋 Secuencial → sigue el orden de los archivos (001, 002, 003...)\n"
             "• 📌 Solo elegidos → publica la Cola de publicación del Gestor de Mensajes\n"
             "• 🔀 Híbrido → primero los de la cola y completa con aleatorio o secuencial\n\n"
             "Los 📌 Mensajes fijos de una tarea no salen en este botón ni en la rotación normal "
             "(ver 'Mensajes fijos').\n\n"
             "Configuración relacionada:\n"
             "• Configurador → pestaña Publicar Bíblico (navegador, intentos)\n"
             "• Configurador → pestaña Mensajes (modo, cantidad, memoria, hashtags)\n\n"
             "⚠️ Cantidad mayor a 1, Solo elegidos e Híbrido requieren versión Completa"),

            ("📱  Enviar Oraciones por WhatsApp",
             "📱 ENVIAR ORACIONES POR WHATSAPP\n\n"
             "Envía un llamado de oración a los grupos y contactos configurados en WhatsApp.\n\n"
             "¿Qué hace?\n"
             "• Muestra tus destinatarios por defecto ya marcados\n"
             "• Te deja elegir quién recibe la oración en este envío y con qué mensaje\n"
             "• Abre WhatsApp Web (con su ventana de consola) y envía solo a los que marcaste\n"
             "• Cierra solo los avisos de WhatsApp Web (por ejemplo 'Novedades') si aparecen\n"
             "• Usa mensajes distintos para grupos e individuales\n\n"
             "Destinatarios de este envío:\n"
             "• Lo que marques aplica solo a este envío\n"
             "• Tu lista por defecto no cambia, salvo que marques\n"
             "  '💾 Guardar también como destinatarios por defecto'\n"
             "• Cada Tarea Automática puede usar la lista por defecto o sus propios destinatarios\n\n"
             "Configuración relacionada:\n"
             "• Configurador → pestaña Oraciones (navegador, grupos, mensajes, destinatarios)\n\n"
             "⚠️ Requiere versión Completa"),

            ("🎬  Extraer Predicaciones",
             "🎬 EXTRAER PREDICACIONES\n\n"
             "Busca enlaces de predicaciones y los deja en cola para publicarlos después en Facebook "
             "(y enviarlos por correo).\n\n"
             "Fuentes (Configurador → Extractor):\n"
             "• 📁 Carpeta de archivos: lee los .txt y .docx (Word) de la carpeta que elijas\n"
             "• 💬 Grupo de WhatsApp: abre WhatsApp Web y revisa el grupo configurado\n"
             "• Puedes usar una, la otra o ambas. Con ambas, primero revisa la carpeta y solo abre "
             "WhatsApp si todavía faltan prédicas\n\n"
             "Carpeta en Google Drive:\n"
             "• Instala 'Google Drive para escritorio': tu Drive aparece como una carpeta de Windows "
             "(por ejemplo G:\\Mi unidad\\Prédicas)\n"
             "• Elige esa carpeta y todo lo que subas a Drive (incluso desde el celular) se revisa solo\n\n"
             "¿Qué hace?\n"
             "• Reconoce enlaces de YouTube, Facebook, Instagram, TikTok y Threads\n"
             "• En WhatsApp sube por la conversación buscando enlaces más antiguos y cierra avisos\n"
             "• Se detiene cuando hay 5 prédicas pendientes\n"
             "• Nunca repite un enlace ya publicado o que ya está en cola\n"
             "• Guarda cada enlace en 'cola-facebook\\pendientes'\n\n"
             "⚠️ Requiere versión Completa"),

            ("📤  Publicar Prédica Extraída",
             "📤 PUBLICAR PRÉDICA EXTRAÍDA EN FACEBOOK\n\n"
             "Publica en Facebook, una por una, las predicaciones extraídas del grupo de WhatsApp.\n\n"
             "¿Qué hace?\n"
             "• Toma la primera prédica de 'cola-facebook\\pendientes'\n"
             "• Agrega el texto introductorio configurado\n"
             "• Publica el enlace en Facebook con vista previa\n"
             "• La mueve a 'cola-facebook\\publicados' y la anota en el historial\n"
             "• Si encuentra una repetida o ya publicada, la descarta sin publicarla\n\n"
             "¿Cuándo usarlo?\n"
             "• Después de haber extraído predicaciones\n"
             "• El botón aparece desactivado si no hay pendientes\n"
             "• En las tareas, 'Publicar Prédica' siempre va después de 'Extraer'\n\n"
             "Configuración relacionada:\n"
             "• Configurador → pestaña Extractor (texto introductorio)\n\n"
             "⚠️ Requiere versión Completa"),

            ("✉️  Enviar por Correo",
             "✉️ ENVIAR MENSAJE POR CORREO\n\n"
             "Envía por correo electrónico los mensajes bíblicos y las prédicas a tu lista de destinatarios.\n\n"
             "¿Qué envía?\n"
             "• Si en esa misma ejecución se publicó algo en Facebook, envía exactamente eso\n"
             "• Si no, envía un mensaje bíblico (mensajes fijos de la tarea o rotación normal) "
             "y la siguiente prédica pendiente que aún no se haya enviado por correo\n"
             "• Las prédicas enviadas por correo siguen pendientes para Facebook\n"
             "• En Configurador → Correo eliges si enviar mensajes bíblicos, prédicas o ambos\n\n"
             "¿Cómo envía?\n"
             "• Un correo por destinatario: nadie ve los correos de los demás\n"
             "• Asunto: la primera línea del mensaje (puedes cambiarlo)\n"
             "• Al final agrega una línea para que puedan pedir no recibir más\n"
             "• Se puede usar desde ⚡ Acciones, en la Secuencia o en cada Tarea Automática\n\n"
             "Destinatarios:\n"
             "• Configurador → Correo → 👥 Destinatarios de correo\n"
             "• ✅ = recibe por defecto · ⬜ = solo si una tarea lo elige\n"
             "• Cada tarea puede usar los de por defecto o elegir los suyos\n\n"
             "Antes de usarlo mira 'Cómo configurar el correo'.\n\n"
             "⚠️ Requiere versión Completa"),

            ("🔐  Cómo configurar el correo",
             "🔐 CÓMO CONFIGURAR EL CORREO\n\n"
             "Gmail, Outlook y Yahoo no permiten que un programa use tu contraseña normal. "
             "Necesitas una CONTRASEÑA DE APLICACIÓN: un código que solo sirve para enviar correo "
             "y que puedes borrar cuando quieras.\n\n"
             "Gmail, paso a paso:\n"
             "1. Activa la Verificación en 2 pasos de tu cuenta de Google\n"
             "   (myaccount.google.com/signinoptions/twosv)\n"
             "2. Entra a myaccount.google.com/apppasswords\n"
             "3. Escribe un nombre, por ejemplo 'AutomaPro Mensajes Biblicos', y presiona Crear\n"
             "4. Copia el código de 16 letras (sin tomarle captura ni compartirlo)\n"
             "5. Configurador → pestaña Correo:\n"
             "   • Elige Gmail, escribe tu correo y el nombre que verán\n"
             "   • Pega el código en 'Contraseña de aplicación'\n"
             "   • Presiona 🧪 Probar conexión: te llega un correo de prueba\n"
             "   • Presiona 💾 Guardar\n\n"
             "¿Dónde queda la contraseña?\n"
             "• Cifrada en el Administrador de credenciales de Windows, no en un archivo\n"
             "• No necesitas anotarla: si la pierdes, bórrala en Google y crea otra\n\n"
             "Outlook y Yahoo también usan contraseña de aplicación desde la seguridad de su cuenta. "
             "Para otro proveedor elige 'Otro' y escribe su servidor y puerto SMTP.\n\n"
             "Gmail permite alrededor de 500 correos por día."),

            ("📌  Mensajes fijos y cola",
             "📌 MENSAJES FIJOS Y COLA DE PUBLICACIÓN\n\n"
             "Hay dos formas de decidir tú qué mensaje se publica:\n\n"
             "📌 Cola de publicación (Gestor de Mensajes)\n"
             "• Eliges mensajes con '📌 Elegir para publicar' y los ordenas con ↑ ↓\n"
             "• Se usa en los modos Solo elegidos o Híbrido (Configurador → Mensajes)\n"
             "• Cada mensaje sale UNA vez y se quita de la cola\n"
             "• Afecta a todas las tareas y al Panel\n"
             "• Ideal para: 'esta semana quiero que salgan estos mensajes'\n\n"
             "📌 Mensajes fijos (cada Tarea Automática)\n"
             "• Gestor de Tareas → pestaña ⚡ Acciones → '📌 Mensajes fijos: ✅ Elegir…'\n"
             "• La tarea publica SIEMPRE esos mensajes, todos los días\n"
             "• Si son varios se turnan según la cantidad de la tarea (024 → 025 → 026 → 024...)\n"
             "• Dejan de salir en la rotación normal de las demás tareas y del Panel\n"
             "• Ideal para anuncios o campañas (por ejemplo, un anuncio diario a las 12:00)\n\n"
             "⚠️ Requiere versión Completa"),

            ("⚡  Ejecutar Secuencia",
             "⚡ EJECUTAR SECUENCIA CONFIGURADA\n\n"
             "Ejecuta, una tras otra, las acciones activadas en el orden que definiste.\n\n"
             "¿Qué hace?\n"
             "• Lee las acciones activas de Configurador → Secuencia\n"
             "• Las ejecuta en orden (Bíblico, Extraer, Prédica, Oraciones, Correo)\n"
             "• Cada acción espera a que la anterior termine\n"
             "• 'Publicar Prédica' siempre va después de 'Extraer'\n\n"
             "¿Cuándo usarlo?\n"
             "• Para correr todo el flujo de una sola vez\n"
             "• También es el valor inicial de las Tareas Automáticas nuevas\n\n"
             "⚠️ Requiere versión Completa"),

            ("🗓️  Tareas Automáticas",
             "🗓️ TAREAS AUTOMÁTICAS\n\n"
             "Programa el sistema para que trabaje solo, en los días y horas que elijas.\n\n"
             "Pestaña 📅 Horario\n"
             "• Nombre, frecuencia (diaria o semanal), días y hora\n\n"
             "Pestaña ⚡ Acciones\n"
             "• Qué hace la tarea y en qué orden (Bíblico, Extraer, Prédica, Oraciones, Correo)\n"
             "• 📖 Cuántos mensajes bíblicos publica (1 a 10, o la configuración general)\n"
             "• 📌 Mensajes fijos: mensajes que esta tarea publica siempre\n"
             "• 📱 Destinatarios de oraciones propios o los de por defecto\n"
             "• ✉️ Destinatarios de correo propios o los de por defecto\n\n"
             "¿Cómo funciona?\n"
             "• Usa el Programador de Tareas de Windows: funciona con el panel cerrado\n"
             "• El equipo debe estar encendido a la hora programada\n"
             "• Cada acción muestra su ventana de consola mientras trabaja\n\n"
             "Si falta configuración:\n"
             "• Aparece un aviso con cuenta regresiva de 30 segundos\n"
             "• Si nadie responde, se omite solo esa acción y siguen las demás\n"
             "• Todo queda anotado en 'registro_tareas.log'\n\n"
             "⚠️ Requiere versión Completa"),

            ("⚙️  Configurador",
             "⚙️ CONFIGURADOR\n\n"
             "Aquí ajustas cómo trabaja cada parte del sistema.\n\n"
             "Pestañas:\n"
             "• Publicar Bíblico → navegador, tiempos e intentos\n"
             "• Mensajes → modo de selección, cantidad, memoria, hashtags\n"
             "• Extractor → fuentes (grupo de WhatsApp y/o carpeta), navegador, texto introductorio\n"
             "• Oraciones → navegador, grupos y contactos, mensajes, destinatarios por defecto\n"
             "• Correo → cuenta que envía, qué enviar, destinatarios de correo, prueba de conexión\n"
             "• Secuencia → acciones activas y su orden\n"
             "• Avanzado → perfil del navegador, ventana maximizada, tiempo mínimo entre publicaciones\n\n"
             "Recuerda presionar 💾 Guardar antes de cerrar."),

            ("📝  Gestor de Mensajes",
             "📝 GESTOR DE MENSAJES\n\n"
             "Editor para crear, editar y organizar tus mensajes bíblicos.\n\n"
             "¿Qué puedes hacer?\n"
             "• Ver todos los mensajes de tu carpeta 'mensajes'\n"
             "• Crear (➕ Nuevo), editar y eliminar mensajes\n"
             "• 📌 Elegir mensajes para la Cola de publicación y ordenarla (versión Completa)\n\n"
             "Consejos:\n"
             "• Un mensaje por archivo (mensaje-001.txt, mensaje-002.txt...)\n"
             "• La primera línea también se publica y se usa como asunto del correo\n"
             "• Puedes usar saltos de línea, emojis y enlaces https://\n"
             "• Algunos emojis se ven como cuadros en el editor pero salen bien en Facebook"),

            ("📊  Estadísticas",
             "📊 ESTADÍSTICAS\n\n"
             "Resumen del historial de publicaciones en Facebook.\n\n"
             "¿Qué muestra?\n"
             "• Total de publicaciones, exitosas y fallidas\n"
             "• Tasa de éxito y tiempo promedio por publicación\n"
             "• Fecha de la última publicación\n\n"
             "Los datos se guardan en 'registro_publicaciones.json'. "
             "Los envíos por correo se anotan aparte en 'correo\\registro_envios.json'."),

            ("🔄  Actualizaciones",
             "🔄 ACTUALIZACIONES\n\n"
             "El sistema revisa si hay una versión nueva:\n"
             "• Al abrir el Panel de Control\n"
             "• Al terminar una Tarea Automática (como máximo un aviso por día)\n\n"
             "En el aviso puedes elegir:\n"
             "• Actualizar ahora → descarga e instala la versión nueva\n"
             "• Más tarde → se vuelve a avisar otro día\n"
             "  (si nadie responde en 30 segundos, se elige Más tarde)\n\n"
             "Al actualizar se conserva todo lo tuyo:\n"
             "• Mensajes creados, editados o borrados\n"
             "• Tareas automáticas y su configuración\n"
             "• Configuración, destinatarios, cola de prédicas e historial\n"
             "• La contraseña del correo (queda en Windows)"),
        ]

        header = tk.Frame(ventana, bg="#1a73e8", pady=12)
        header.pack(fill='x')
        tk.Label(header, text="❓ Centro de Ayuda",
                 font=("Segoe UI", 14, "bold"), bg="#1a73e8", fg="white").pack()
        tk.Label(header, text="Selecciona una opción para ver su explicación",
                 font=("Segoe UI", 9), bg="#1a73e8", fg="white").pack()

        cuerpo = tk.Frame(ventana, bg="#f0f0f0")
        cuerpo.pack(fill='both', expand=True, padx=15, pady=12)

        panel_izq = tk.Frame(cuerpo, bg="#f0f0f0", width=245)
        panel_izq.pack(side='left', fill='y', padx=(0, 10))
        panel_izq.pack_propagate(False)

        tk.Label(panel_izq, text="Opciones", font=("Segoe UI", 9, "bold"),
                 bg="#f0f0f0", fg="#555").pack(anchor='w', pady=(0, 5))

        panel_der = tk.Frame(cuerpo, bg="white", relief='solid', borderwidth=1)
        panel_der.pack(side='left', fill='both', expand=True)

        texto_detalle = tk.Text(panel_der, font=("Segoe UI", 10), bg="white",
                                fg="#333", wrap='word', relief='flat',
                                padx=15, pady=12, state='disabled', cursor="arrow")
        scroll = tk.Scrollbar(panel_der, command=texto_detalle.yview)
        texto_detalle.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        texto_detalle.pack(fill='both', expand=True)

        botones = []

        def seleccionar(idx):
            for i, btn in enumerate(botones):
                btn.config(bg="#1a73e8" if i == idx else "white",
                           fg="white" if i == idx else "#333")
            texto_detalle.config(state='normal')
            texto_detalle.delete('1.0', tk.END)
            texto_detalle.insert(tk.END, TEMAS[idx][1])
            texto_detalle.config(state='disabled')

        for i, (nombre, _) in enumerate(TEMAS):
            btn = tk.Button(panel_izq, text=nombre, font=("Segoe UI", 9),
                            bg="white", fg="#333", anchor='w', padx=8, pady=5,
                            relief='solid', borderwidth=1, cursor="hand2",
                            command=lambda idx=i: seleccionar(idx))
            btn.pack(fill='x', pady=2)
            botones.append(btn)

        seleccionar(0)

        tk.Button(ventana, text="Cerrar", font=("Segoe UI", 10),
                  bg="#6c757d", fg="white", width=12,
                  command=lambda: [ventana.grab_release(), ventana.destroy()]
                  ).pack(pady=10)

        ventana.protocol("WM_DELETE_WINDOW",
                         lambda: [ventana.grab_release(), ventana.destroy()])
        self._centrar_ventana(ventana, 860, 640)
        ventana.deiconify()

    def _toast(self, titulo, mensaje, duracion=3000, color="#28a745"):
        """Delega al sistema centralizado de toasts"""
        from compartido.toast import Toast
        if color == Toast.COLOR_ERROR or color == "#dc3545":
            Toast.error(self.root, f"{titulo}\n{mensaje}", duracion)
        elif color == Toast.COLOR_ADVERTENCIA or color == "#e65100":
            Toast.advertencia(self.root, f"{titulo}\n{mensaje}", duracion)
        elif color == Toast.COLOR_INFO or color == "#1a73e8":
            Toast.info(self.root, f"{titulo}\n{mensaje}", duracion)
        else:
            Toast.exito(self.root, f"{titulo}\n{mensaje}", duracion)

    def ejecutar(self):
        self.root.mainloop()


def _verificar_wizard_completado():
    """Si no hay licencia configurada, lanza el wizard y termina"""
    import subprocess
    gestor = GestorLicencias("MensajesBiblicos")
    if not os.path.exists(gestor.archivo_config):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            wizard = os.path.join(base_dir, "WizardMensajes.exe")
        else:
            wizard = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wizard_primera_vez.py")

        if os.path.exists(wizard):
            subprocess.Popen([wizard])
        else:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning(
                "Configuración requerida",
                "Por favor ejecuta WizardMensajes.exe para configurar el sistema."
            )
            root.destroy()
        return False
    return True


def main():
    if not _verificar_wizard_completado():
        return
    panel = PanelControl()
    panel.ejecutar()


if __name__ == "__main__":
    main()