import os
import sys
import json
import configparser
import tkinter as tk
from tkinter import ttk, messagebox
from compartido.toast import Toast
from compartido.gestor_archivos import leer_mensajes_elegidos
from publicadores.publicador_correo import (
    PROVEEDORES, leer_config_correo, leer_contrasena, guardar_contrasena, probar_conexion,
    leer_destinatarios_correo, guardar_destinatarios_correo, falta_configuracion_correo
)


class ConfiguradorGUI:
    """Interfaz gráfica para configurar el sistema de Mensajes Bíblicos"""

    def __init__(self):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--pestana', default=None)
        parser.add_argument('--ejecutar-despues', action='store_true', default=False)
        args, _ = parser.parse_known_args()
        self.pestana_inicial = args.pestana
        self.ejecutar_despues = args.ejecutar_despues

        self.config = configparser.RawConfigParser(delimiters=('=',))
        self.cambios = {}

        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.archivo_config = os.path.join(self.base_dir, "config_global.txt")
        self.archivo_grupos = os.path.join(self.base_dir, "llamados-oracion", "grupos.json")

        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('AutomaPro.ConfiguradorMensajes')
        except Exception:
            pass

        self.root = tk.Tk()
        self.root.withdraw()

        self.root.title("⚙️ Configurador - Mensajes Bíblicos")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f0f0")

        try:
            base_ico = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            ico = os.path.join(base_ico, 'iconos', 'settings.ico')
            self.root.iconbitmap(ico)
            # default= hace que las subventanas (Toplevel) hereden el ícono en vez de la pluma de Tkinter
            self.root.iconbitmap(default=ico)
        except Exception:
            pass

        width = 700
        height = 660
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        self._cargar_config()
        self.es_full = self._verificar_licencia_full()
        self._construir_ui()

        self.root.deiconify()

    def _verificar_licencia_full(self):
        """Verifica si la licencia es FULL/MASTER — solo cache, sin llamada de red"""
        try:
            from gestor_licencias import GestorLicencias
            gl = GestorLicencias("MensajesBiblicos")
            cache = gl._obtener_cache_local()
            if cache and cache.get('valida'):
                tipo = cache.get('tipo', 'TRIAL')
                return tipo in ['FULL', 'MASTER'] or cache.get('es_developer_permanente', False)
            return False
        except Exception:
            return False

    def _cargar_config(self):
        if os.path.exists(self.archivo_config):
            self.config.read(self.archivo_config, encoding='utf-8')

    def _guardar_config(self):
        try:
            self.config['GENERAL']['navegador'] = self.var_nav_facebook.get()

            sel = self.var_seleccion.get()
            self.config['MENSAJES']['seleccion'] = sel if sel else 'aleatorio'
            self.config['MENSAJES']['relleno_hibrido'] = self.var_relleno_hibrido.get()
            self.config['MENSAJES']['cantidad_por_ejecucion'] = self._cantidad_valida() if self.es_full else '1'
            self.config['MENSAJES']['historial_evitar_repetir'] = self.var_historial.get()
            self.config['MENSAJES']['agregar_hashtags'] = self.var_hashtags.get()
            self.config['MENSAJES']['hashtags'] = self.var_hashtags_texto.get()

            self.config['PUBLICACION']['tiempo_entre_intentos'] = self.var_tiempo_intentos.get()
            self.config['PUBLICACION']['max_intentos_por_publicacion'] = self.var_max_intentos.get()
            self.config['PUBLICACION']['espera_despues_publicar'] = self.var_espera.get()

            if self.es_full:
                if not self.config.has_section('PREDICACIONES'):
                    self.config.add_section('PREDICACIONES')
                self.config['PREDICACIONES']['activar_predicaciones'] = 'si'
                self.config['PREDICACIONES']['nombre_grupo_whatsapp'] = self.var_grupo_predicaciones.get()
                self.config['PREDICACIONES']['mensajes_por_extraccion'] = self.var_mensajes_extraccion.get()
                self.config['PREDICACIONES']['navegador'] = self.var_nav_predicaciones.get()
                self.config['PREDICACIONES']['texto_introduccion_predica'] = self.var_mensaje_intro_predica.get()
                if not self.var_fuente_whatsapp.get() and not self.var_fuente_carpeta.get():
                    messagebox.showerror("❌ Extractor", "Marca al menos una fuente de predicaciones (WhatsApp o carpeta)")
                    return
                if self.var_fuente_carpeta.get() and not os.path.isdir(self.var_carpeta_predicaciones.get().strip()):
                    messagebox.showerror("❌ Extractor", "La carpeta de predicaciones no existe. Elígela con '📁 Elegir…'")
                    return
                self.config['PREDICACIONES']['extraer_de_whatsapp'] = 'si' if self.var_fuente_whatsapp.get() else 'no'
                self.config['PREDICACIONES']['extraer_de_carpeta'] = 'si' if self.var_fuente_carpeta.get() else 'no'
                self.config['PREDICACIONES']['carpeta_predicaciones'] = self.var_carpeta_predicaciones.get().strip()

            if self.es_full:
                if not self.config.has_section('ORACIONES'):
                    self.config.add_section('ORACIONES')
                self.config['ORACIONES']['navegador'] = self.var_nav_oraciones.get()
                carpeta_oraciones = os.path.join(self.base_dir, 'llamados-oracion')
                archivo_oraciones = os.path.join(carpeta_oraciones, 'mensajes_oracion.txt')
                if not os.path.exists(archivo_oraciones):
                    os.makedirs(carpeta_oraciones, exist_ok=True)
                    with open(archivo_oraciones, 'w', encoding='utf-8') as f:
                        f.write(
                            "[GRUPOS]\n"
                            "🙏 Hermanos, tomemos un momento para orar juntos. ¡Los invito a elevar una oración!\n"
                            "🙏 Familia, detengámonos un instante para orar. ¡El Señor nos escucha!\n\n"
                            "[INDIVIDUALES]\n"
                            "🙏 Hola, te invito a un momento de oración. ¡Oremos juntos!\n"
                            "🙏 Amigo/a, ¿podemos orar juntos un momento? ¡Dios tiene algo para ti hoy!\n"
                        )

            if self.es_full:
                if not self.config.has_section('CORREO'):
                    self.config.add_section('CORREO')
                remitente = self.var_correo_remitente.get().strip()
                self.config['CORREO']['proveedor'] = self.var_correo_proveedor.get()
                self.config['CORREO']['servidor'] = self.var_correo_servidor.get().strip()
                self.config['CORREO']['puerto'] = self.var_correo_puerto.get().strip()
                self.config['CORREO']['seguridad'] = PROVEEDORES.get(self.var_correo_proveedor.get(), PROVEEDORES['otro'])[3] \
                    if self.var_correo_proveedor.get() != 'otro' else self.config['CORREO'].get('seguridad', 'starttls')
                self.config['CORREO']['remitente'] = remitente
                self.config['CORREO']['nombre_remitente'] = self.var_correo_nombre.get().strip()
                self.config['CORREO']['asunto'] = self.var_correo_asunto.get().strip() or '{titulo}'
                if not self.var_correo_biblicos.get() and not self.var_correo_predicas.get():
                    messagebox.showerror("❌ Correo", "Marca al menos una opción en 'Qué enviar por correo'")
                    return
                self.config['CORREO']['enviar_biblicos'] = 'si' if self.var_correo_biblicos.get() else 'no'
                self.config['CORREO']['enviar_predicas'] = 'si' if self.var_correo_predicas.get() else 'no'
                if remitente and '@' not in remitente:
                    messagebox.showerror("❌ Correo", "Escribe el correo completo, por ejemplo nombre@gmail.com")
                    return
                contrasena = self.var_correo_contrasena.get().replace(' ', '')
                if contrasena:
                    if not remitente:
                        messagebox.showerror("❌ Correo", "Escribe el correo que envía antes de guardar la contraseña")
                        return
                    if not guardar_contrasena(remitente, contrasena):
                        messagebox.showerror("❌ Correo", "Windows no pudo guardar la contraseña del correo")
                        return
                    self.var_correo_contrasena.set('')

            self.config['NAVEGADOR']['usar_perfil_existente'] = self.var_usar_perfil.get()
            self.config['NAVEGADOR']['maximizar_ventana'] = self.var_maximizar.get()

            self.config['LIMITES']['tiempo_minimo_entre_publicaciones_segundos'] = self.var_tiempo_minimo.get()
            self.config['LIMITES']['permitir_forzar_publicacion_manual'] = self.var_forzar_manual.get()

            if self.es_full and hasattr(self, '_seq_vars') and hasattr(self, '_seq_orden'):
                if not self.config.has_section('SECUENCIA'):
                    self.config.add_section('SECUENCIA')
                activos = [c for c in self._seq_orden if self._seq_vars.get(c, tk.BooleanVar(value=False)).get()]
                if 'publicar_predica' in activos and 'extraer' in activos:
                    if activos.index('publicar_predica') < activos.index('extraer'):
                        idx_pp = activos.index('publicar_predica')
                        idx_ex = activos.index('extraer')
                        activos[idx_pp], activos[idx_ex] = activos[idx_ex], activos[idx_pp]
                self.config['SECUENCIA']['modulos_activos'] = ','.join(activos)

            with open(self.archivo_config, 'w', encoding='utf-8') as f:
                f.write("# ============================================================\n")
                f.write("# CONFIGURACIÓN GLOBAL - PUBLICADOR AUTOMÁTICO FACEBOOK\n")
                f.write("# ============================================================\n\n")
                self.config.write(f)

            # Validaciones post-guardado — advertencias opcionales
            revisar = False
            if self.es_full:
                advertencias = []
                secuencia = self.config.get('SECUENCIA', 'modulos_activos', fallback='')
                lista_seq = [m.strip() for m in secuencia.split(',') if m.strip()]

                if 'extraer' in lista_seq or 'publicar_predica' in lista_seq:
                    grupo = self.var_grupo_predicaciones.get().strip()
                    if not grupo:
                        advertencias.append("• Falta el nombre del grupo de WhatsApp (pestaña Extractor)")

                archivo_grupos = self.archivo_grupos
                grupos_ok = False
                if os.path.exists(archivo_grupos):
                    try:
                        with open(archivo_grupos, 'r', encoding='utf-8') as fg:
                            datos = json.load(fg)
                        grupos_ok = len([g for g in datos.get('grupos', []) if g.get('activo', True)]) > 0
                    except:
                        pass
                if not grupos_ok:
                    advertencias.append("• No hay grupos/contactos de oraciones configurados (pestaña Oraciones)")

                archivo_msg = os.path.join(self.base_dir, 'llamados-oracion', 'mensajes_oracion.txt')
                if not os.path.exists(archivo_msg):
                    advertencias.append("• No hay mensajes de oración configurados (pestaña Oraciones)")

                if 'correo' in lista_seq:
                    problema_correo = falta_configuracion_correo()
                    if problema_correo:
                        advertencias.append(f"• {problema_correo} (pestaña Correo)")

                if advertencias:
                    texto = "Configuración guardada, pero hay items pendientes:\n\n"
                    texto += "\n".join(advertencias)
                    texto += "\n\n¿Deseas revisar la configuración ahora?"
                    revisar = messagebox.askyesno("⚠️ Configuración incompleta", texto)
                else:
                    Toast.exito(self.root, "Configuración guardada correctamente")
            else:
                Toast.exito(self.root, "Configuración guardada correctamente")

            if not revisar:
                if self.ejecutar_despues:
                    import subprocess
                    exe = os.path.join(self.base_dir, "MensajesBiblicos.exe")
                    if os.path.exists(exe):
                        subprocess.Popen([exe])
                self.root.after(3500, self.root.destroy)

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al guardar: {e}")

    def _get(self, seccion, clave, defecto=''):
        try:
            valor = self.config[seccion][clave].split('#')[0].strip()
            return valor if valor else defecto
        except:
            return defecto

    def _cantidad_valida(self):
        try:
            return str(max(1, min(10, int(self.var_cantidad.get()))))
        except (ValueError, tk.TclError):
            return '1'

    def _seccion(self, parent, texto):
        tk.Label(parent, text=texto, font=("Segoe UI", 10, "bold"), bg="#f0f0f0", fg="#333").pack(anchor='w', padx=20, pady=(12, 2))

    def _radio_si_no(self, parent, variable):
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(anchor='w', padx=20, pady=(0, 12))
        for opcion, label in [('si', 'Sí'), ('no', 'No')]:
            tk.Radiobutton(frame, text=label, variable=variable, value=opcion, bg="#f0f0f0", font=("Segoe UI", 10)).pack(side='left', padx=8)

    def _radio_navegador(self, parent, variable):
        frame = tk.Frame(parent, bg="#f0f0f0")
        frame.pack(anchor='w', padx=20, pady=(0, 12))
        for opcion in ['firefox', 'chrome', 'edge']:
            tk.Radiobutton(frame, text=opcion.capitalize(), variable=variable, value=opcion, bg="#f0f0f0", font=("Segoe UI", 10)).pack(side='left', padx=8)

    def _construir_ui(self):
        header = tk.Frame(self.root, bg="#1a73e8", pady=12)
        header.pack(fill='x')
        tk.Label(header, text="⚙️  Configurador - Mensajes Bíblicos", font=("Segoe UI", 14, "bold"), bg="#1a73e8", fg="white").pack()

        style = ttk.Style()
        style.configure('TNotebook.Tab', font=('Segoe UI', 9))

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # ==================== PESTAÑA FACEBOOK ====================
        tab_fb = ttk.Frame(notebook)
        notebook.add(tab_fb, text="▶️ Publicar Bíblico")

        tk.Label(tab_fb, text="Configuración para publicar mensajes bíblicos en Facebook automáticamente",
                 font=("Segoe UI", 9), fg="#555", bg="#f0f0f0").pack(anchor='w', padx=20, pady=(10, 0))

        self._seccion(tab_fb, "🌐 Navegador para publicar en Facebook")
        self.var_nav_facebook = tk.StringVar(value=self._get('GENERAL', 'navegador', 'firefox'))
        self._radio_navegador(tab_fb, self.var_nav_facebook)

        self._seccion(tab_fb, "⏱️ Tiempo entre intentos (segundos)")
        self.var_tiempo_intentos = tk.StringVar(value=self._get('PUBLICACION', 'tiempo_entre_intentos', '3'))
        tk.Spinbox(tab_fb, from_=1, to=30, textvariable=self.var_tiempo_intentos, width=8, font=("Segoe UI", 10)).pack(anchor='w', padx=20, pady=(0, 12))

        self._seccion(tab_fb, "🔄 Máximo de intentos por publicación")
        self.var_max_intentos = tk.StringVar(value=self._get('PUBLICACION', 'max_intentos_por_publicacion', '3'))
        tk.Spinbox(tab_fb, from_=1, to=10, textvariable=self.var_max_intentos, width=8, font=("Segoe UI", 10)).pack(anchor='w', padx=20, pady=(0, 12))

        self._seccion(tab_fb, "⏳ Espera después de publicar (segundos)")
        self.var_espera = tk.StringVar(value=self._get('PUBLICACION', 'espera_despues_publicar', '5'))
        tk.Spinbox(tab_fb, from_=1, to=30, textvariable=self.var_espera, width=8, font=("Segoe UI", 10)).pack(anchor='w', padx=20, pady=(0, 12))

        # ==================== PESTAÑA MENSAJES ====================
        tab_mensajes = ttk.Frame(notebook)
        notebook.add(tab_mensajes, text="📝 Mensajes")

        tk.Label(tab_mensajes, text="Configura cómo se eligen y formatean los mensajes bíblicos al publicar",
                 font=("Segoe UI", 9), fg="#555", bg="#f0f0f0").pack(anchor='w', padx=20, pady=(10, 0))

        seleccion_guardada = self._get('MENSAJES', 'seleccion', 'aleatorio').lower()
        seleccion_guardada = {'aleatoria': 'aleatorio'}.get(seleccion_guardada, seleccion_guardada)
        if seleccion_guardada not in ('aleatorio', 'secuencial', 'elegidos', 'hibrido'):
            seleccion_guardada = 'aleatorio'
        if not self.es_full and seleccion_guardada in ('elegidos', 'hibrido'):
            seleccion_guardada = 'aleatorio'
        self.var_seleccion = tk.StringVar(value=seleccion_guardada)
        self.var_relleno_hibrido = tk.StringVar(value=self._get('MENSAJES', 'relleno_hibrido', 'aleatorio'))
        self.var_cantidad = tk.StringVar(value=self._get('MENSAJES', 'cantidad_por_ejecucion', '1') if self.es_full else '1')

        self._seccion(tab_mensajes, "🎯 Cómo elegir los mensajes a publicar")
        frame_modo = tk.Frame(tab_mensajes, bg="#f0f0f0")
        frame_modo.pack(anchor='w', padx=20, pady=(0, 2))
        for valor, icono, nombre, solo_full in [
            ('aleatorio',  "🎲", "Aleatorio",     False),
            ('secuencial', "📋", "Secuencial",    False),
            ('elegidos',   "📌", "Solo elegidos", True),
            ('hibrido',    "🔀", "Híbrido",       True),
        ]:
            bloqueado = solo_full and not self.es_full
            tk.Radiobutton(frame_modo, text=f"{'🔒' if bloqueado else icono} {nombre}",
                           variable=self.var_seleccion, value=valor, bg="#f0f0f0", font=("Segoe UI", 10),
                           state='disabled' if bloqueado else 'normal').pack(side='left', padx=6)

        frame_relleno = tk.Frame(tab_mensajes, bg="#f0f0f0")
        frame_relleno.pack(anchor='w', padx=40, pady=(0, 6))
        tk.Label(frame_relleno, text="Híbrido completa con:", font=("Segoe UI", 9), fg="#555", bg="#f0f0f0").pack(side='left')
        radios_relleno = []
        for valor, nombre in [('aleatorio', "Aleatorio"), ('secuencial', "Secuencial")]:
            rb = tk.Radiobutton(frame_relleno, text=nombre, variable=self.var_relleno_hibrido, value=valor,
                                bg="#f0f0f0", font=("Segoe UI", 9))
            rb.pack(side='left', padx=6)
            radios_relleno.append(rb)

        def _actualizar_relleno(*_):
            estado = 'normal' if self.var_seleccion.get() == 'hibrido' else 'disabled'
            for rb in radios_relleno:
                rb.config(state=estado)
        self.var_seleccion.trace_add('write', _actualizar_relleno)
        _actualizar_relleno()

        self._seccion(tab_mensajes, "🔢 Mensajes a publicar por ejecución")
        frame_cantidad = tk.Frame(tab_mensajes, bg="#f0f0f0")
        frame_cantidad.pack(anchor='w', padx=20, pady=(0, 2))
        tk.Spinbox(frame_cantidad, from_=1, to=10, textvariable=self.var_cantidad, width=8, font=("Segoe UI", 10),
                   state='normal' if self.es_full else 'disabled').pack(side='left')
        tk.Label(frame_cantidad, text=f"📌 {len(leer_mensajes_elegidos())} elegido(s) en cola",
                 font=("Segoe UI", 9), fg="#555", bg="#f0f0f0").pack(side='left', padx=12)
        tk.Label(tab_mensajes, text="Entre cada mensaje se espera el tiempo mínimo de la pestaña Avanzado",
                 font=("Segoe UI", 8), fg="#777", bg="#f0f0f0").pack(anchor='w', padx=20, pady=(0, 6))

        if not self.es_full:
            tk.Label(tab_mensajes, text="🔒 Cantidad, Solo elegidos e Híbrido requieren versión Completa",
                     font=("Segoe UI", 8), bg="#fff3cd", fg="#856404").pack(anchor='w', padx=20, pady=(0, 6))

        self._seccion(tab_mensajes, "🧠 Memoria: últimos N mensajes a evitar repetir")
        self.var_historial = tk.StringVar(value=self._get('MENSAJES', 'historial_evitar_repetir', '5'))
        tk.Spinbox(tab_mensajes, from_=0, to=20, textvariable=self.var_historial, width=8, font=("Segoe UI", 10)).pack(anchor='w', padx=20, pady=(0, 12))

        self._seccion(tab_mensajes, "# Agregar hashtags automáticamente")
        self.var_hashtags = tk.StringVar(value=self._get('MENSAJES', 'agregar_hashtags', 'no'))
        self._radio_si_no(tab_mensajes, self.var_hashtags)

        self._seccion(tab_mensajes, "📎 Hashtags (separados por comas)")
        self.var_hashtags_texto = tk.StringVar(value=self._get('MENSAJES', 'hashtags', '#Fe,#Biblia'))
        tk.Entry(tab_mensajes, textvariable=self.var_hashtags_texto, width=40, font=("Segoe UI", 10)).pack(anchor='w', padx=20, pady=(0, 12))

        # ==================== PESTAÑA EXTRACTOR WHATSAPP ====================
        tab_pred = ttk.Frame(notebook)
        notebook.add(tab_pred, text="🎬 Extractor")

        tk.Label(tab_pred, text="De dónde se extraen los enlaces de predicaciones: un grupo de WhatsApp y/o una carpeta de archivos",
                 font=("Segoe UI", 9), fg="#555", bg="#f0f0f0").pack(anchor='w', padx=20, pady=(10, 0))

        if not self.es_full:
            banner_pred = tk.Frame(tab_pred, bg="#fff3cd", pady=6)
            banner_pred.pack(fill='x', padx=20, pady=(8, 0))
            tk.Label(banner_pred, text="🔒 Estas funciones están disponibles en la versión Completa",
                     font=("Segoe UI", 9, "bold"), fg="#856404", bg="#fff3cd").pack()

        estado_pred = 'normal' if self.es_full else 'disabled'
        self._seccion(tab_pred, "📂 Fuentes de predicaciones")
        self.var_fuente_whatsapp = tk.BooleanVar(value=self._get('PREDICACIONES', 'extraer_de_whatsapp', 'si') == 'si')
        self.var_fuente_carpeta = tk.BooleanVar(value=self._get('PREDICACIONES', 'extraer_de_carpeta', 'no') == 'si')
        self.var_carpeta_predicaciones = tk.StringVar(value=self._get('PREDICACIONES', 'carpeta_predicaciones', ''))
        fila_fuentes = tk.Frame(tab_pred, bg="#f0f0f0")
        fila_fuentes.pack(anchor='w', padx=20)
        tk.Checkbutton(fila_fuentes, text="💬 Grupo de WhatsApp", variable=self.var_fuente_whatsapp, bg="#f0f0f0",
                       font=("Segoe UI", 10), state=estado_pred).pack(side='left', padx=(0, 15))
        tk.Checkbutton(fila_fuentes, text="📁 Carpeta de archivos (.txt, .docx)", variable=self.var_fuente_carpeta,
                       bg="#f0f0f0", font=("Segoe UI", 10), state=estado_pred).pack(side='left')
        fila_carpeta = tk.Frame(tab_pred, bg="#f0f0f0")
        fila_carpeta.pack(anchor='w', padx=20, pady=(4, 0))
        tk.Entry(fila_carpeta, textvariable=self.var_carpeta_predicaciones, width=52, font=("Segoe UI", 9),
                 state=estado_pred).pack(side='left')

        def elegir_carpeta():
            from tkinter import filedialog
            ruta = filedialog.askdirectory(parent=self.root, title="Carpeta con archivos de predicaciones",
                                           initialdir=self.var_carpeta_predicaciones.get() or None)
            if ruta:
                self.var_carpeta_predicaciones.set(os.path.normpath(ruta))
                self.var_fuente_carpeta.set(True)

        tk.Button(fila_carpeta, text="📁 Elegir…", font=("Segoe UI", 9), state=estado_pred,
                  command=elegir_carpeta).pack(side='left', padx=(8, 0))
        tk.Label(tab_pred, text="Puede ser una carpeta de Google Drive para escritorio (ej. G:\\Mi unidad\\Prédicas). "
                                "Con ambas fuentes, primero revisa la carpeta y luego WhatsApp si faltan prédicas.",
                 font=("Segoe UI", 8), fg="gray", bg="#f0f0f0", wraplength=620, justify='left').pack(anchor='w', padx=20, pady=(2, 4))

        self._seccion(tab_pred, "👥 Nombre del grupo de WhatsApp (ORIGEN de predicaciones)")
        tk.Label(tab_pred, text="⚠️  Debe ser EXACTAMENTE igual a como aparece en WhatsApp", font=("Segoe UI", 8), fg="gray", bg="#f0f0f0").pack(anchor='w', padx=20)
        self.var_grupo_predicaciones = tk.StringVar(value=self._get('PREDICACIONES', 'nombre_grupo_whatsapp', ''))
        tk.Entry(tab_pred, textvariable=self.var_grupo_predicaciones, width=40, font=("Segoe UI", 10),
                 state='normal' if self.es_full else 'disabled').pack(anchor='w', padx=20, pady=(0, 12))

        self._seccion(tab_pred, "📦 Predicaciones a extraer por vez")
        self.var_mensajes_extraccion = tk.StringVar(value=self._get('PREDICACIONES', 'mensajes_por_extraccion', '10'))
        tk.Spinbox(tab_pred, from_=1, to=50, textvariable=self.var_mensajes_extraccion, width=8,
                   font=("Segoe UI", 10), state='normal' if self.es_full else 'disabled').pack(anchor='w', padx=20, pady=(0, 12))

        self._seccion(tab_pred, "🌐 Navegador para extracción de predicaciones")
        self.var_nav_predicaciones = tk.StringVar(value=self._get('PREDICACIONES', 'navegador', 'firefox'))
        frame_nav_pred = tk.Frame(tab_pred, bg="#f0f0f0")
        frame_nav_pred.pack(anchor='w', padx=20)
        for val, lbl in [('firefox', 'Firefox'), ('chrome', 'Chrome'), ('edge', 'Edge')]:
            tk.Radiobutton(frame_nav_pred, text=lbl, variable=self.var_nav_predicaciones, value=val,
                           bg="#f0f0f0", font=("Segoe UI", 10),
                           state='normal' if self.es_full else 'disabled').pack(side='left', padx=(0, 15))

        self._seccion(tab_pred, "💬 Mensaje introductorio al publicar prédica")
        tk.Label(tab_pred, text="Se agrega antes del enlace. Si está vacío, publica solo el enlace.",
                 font=("Segoe UI", 8), fg="gray", bg="#f0f0f0").pack(anchor='w', padx=20)
        self.var_mensaje_intro_predica = tk.StringVar(value=self._get('PREDICACIONES', 'texto_introduccion_predica', ''))
        tk.Entry(tab_pred, textvariable=self.var_mensaje_intro_predica, width=50, font=("Segoe UI", 10),
                 state='normal' if self.es_full else 'disabled').pack(anchor='w', padx=20, pady=(0, 12))

        # ==================== PESTAÑA ORACIONES ====================
        tab_ora = ttk.Frame(notebook)
        notebook.add(tab_ora, text="📱 Oraciones")

        tk.Label(tab_ora, text="Configuración para enviar llamados de oración a grupos/contactos de WhatsApp",
                 font=("Segoe UI", 9), fg="#555", bg="#f0f0f0").pack(anchor='w', padx=20, pady=(10, 0))

        if not self.es_full:
            banner_ora = tk.Frame(tab_ora, bg="#fff3cd", pady=6)
            banner_ora.pack(fill='x', padx=20, pady=(8, 0))
            tk.Label(banner_ora, text="🔒 Estas funciones están disponibles en la versión Completa",
                     font=("Segoe UI", 9, "bold"), fg="#856404", bg="#fff3cd").pack()

        self._seccion(tab_ora, "🌐 Navegador para envío de oraciones")
        self.var_nav_oraciones = tk.StringVar(value=self._get('ORACIONES', 'navegador', 'firefox'))
        frame_nav_ora = tk.Frame(tab_ora, bg="#f0f0f0")
        frame_nav_ora.pack(anchor='w', padx=20)
        for val, lbl in [('firefox', 'Firefox'), ('chrome', 'Chrome'), ('edge', 'Edge')]:
            tk.Radiobutton(frame_nav_ora, text=lbl, variable=self.var_nav_oraciones, value=val,
                           bg="#f0f0f0", font=("Segoe UI", 10),
                           state='normal' if self.es_full else 'disabled').pack(side='left', padx=(0, 15))

        self._seccion(tab_ora, "⚙️ Gestión de oraciones")
        frame_btns_ora = tk.Frame(tab_ora, bg="#f0f0f0")
        frame_btns_ora.pack(fill='x', padx=20, pady=(5, 5))

        tk.Button(frame_btns_ora,
            text="👥  Gestionar grupos y contactos" if self.es_full else "🔒  Gestionar grupos y contactos  —  versión Completa",
            font=("Segoe UI", 10, "bold") if self.es_full else ("Segoe UI", 10),
            bg="#1a73e8" if self.es_full else "#e0e0e0",
            fg="white" if self.es_full else "#9e9e9e",
            command=self._abrir_gestor_grupos if self.es_full else lambda: messagebox.showinfo(
                "🔒 Versión Completa", "Adquiere la versión Completa en automapro.com para gestionar grupos.")
        ).pack(fill='x', pady=(0, 8), ipady=6)

        tk.Button(frame_btns_ora,
            text="📝  Gestionar mensajes de oración" if self.es_full else "🔒  Gestionar mensajes de oración  —  versión Completa",
            font=("Segoe UI", 10, "bold") if self.es_full else ("Segoe UI", 10),
            bg="#28a745" if self.es_full else "#e0e0e0",
            fg="white" if self.es_full else "#9e9e9e",
            command=self._abrir_gestor_mensajes_oracion if self.es_full else lambda: messagebox.showinfo(
                "🔒 Versión Completa", "Adquiere la versión Completa en automapro.com para gestionar mensajes.")
        ).pack(fill='x', pady=(0, 8), ipady=6)

        tk.Button(frame_btns_ora,
            text="✅  Seleccionar destinatarios por defecto" if self.es_full else "🔒  Seleccionar destinatarios  —  versión Completa",
            font=("Segoe UI", 10, "bold") if self.es_full else ("Segoe UI", 10),
            bg="#17a2b8" if self.es_full else "#e0e0e0",
            fg="white" if self.es_full else "#9e9e9e",
            command=self._abrir_selector_destinatarios if self.es_full else lambda: messagebox.showinfo(
                "🔒 Versión Completa", "Adquiere la versión Completa en automapro.com.")
        ).pack(fill='x', ipady=6)

        # ==================== PESTAÑA CORREO ====================
        tab_correo = ttk.Frame(notebook)
        notebook.add(tab_correo, text="✉️ Correo")
        self._construir_tab_correo(tab_correo)

        # ==================== PESTAÑA SECUENCIA ====================
        if self.es_full:
            tab_seq = ttk.Frame(notebook)
            notebook.add(tab_seq, text="⚡ Secuencia")

            tk.Label(tab_seq,
                text="Define qué módulos se ejecutan y en qué orden al usar 'Ejecutar Secuencia'. "
                     "También es el valor inicial de las tareas automáticas nuevas; cada tarea guarda después sus propias acciones.",
                font=("Segoe UI", 9), bg="#f0f0f0", fg="#555", wraplength=560, justify='left'
            ).pack(anchor='w', padx=20, pady=(10, 0))

            banner_seq = tk.Frame(tab_seq, bg="#e3f2fd", pady=6)
            banner_seq.pack(fill='x', padx=20, pady=(8, 0))
            tk.Label(banner_seq,
                text="💡 Usa ↑ ↓ para reordenar. 'Publicar Prédica' siempre va después de 'Extraer'.",
                font=("Segoe UI", 8), bg="#e3f2fd", fg="#1a73e8", wraplength=540
            ).pack(padx=10)

            self._seccion(tab_seq, "📋 Módulos a ejecutar (activa/desactiva y ordena)")

            frame_seq = tk.Frame(tab_seq, bg="#f0f0f0")
            frame_seq.pack(fill='x', padx=20, pady=(0, 10))

            modulos_disponibles = [
                ("biblico",          "▶️  Publicar Mensaje Bíblico en Facebook"),
                ("extraer",          "🎬  Extraer Predicaciones (WhatsApp / carpeta)"),
                ("publicar_predica", "📤  Publicar Prédica Extraída en Facebook"),
                ("oraciones",        "📱  Enviar Oraciones por WhatsApp"),
                ("correo",           "✉️  Enviar Mensaje por Correo"),
            ]

            seq_guardada = self._get('SECUENCIA', 'modulos_activos', 'biblico,extraer,publicar_predica')
            seq_activos = set(seq_guardada.split(','))
            seq_lista = [m.strip() for m in seq_guardada.split(',') if m.strip()]
            for clave, _ in modulos_disponibles:
                if clave not in seq_lista:
                    seq_lista.append(clave)

            self._seq_vars = {}
            self._seq_orden = list(seq_lista)
            self._seq_container = tk.Frame(frame_seq, bg="#f0f0f0")
            self._seq_container.pack(fill='x')

            mods_dict = dict(modulos_disponibles)

            def _render_seq():
                for w in self._seq_container.winfo_children():
                    w.destroy()
                for idx, clave in enumerate(self._seq_orden):
                    if clave not in mods_dict:
                        continue
                    label = mods_dict[clave]
                    fila = tk.Frame(self._seq_container, bg="#ffffff", relief='solid', borderwidth=1)
                    fila.pack(fill='x', pady=2)
                    if clave not in self._seq_vars:
                        self._seq_vars[clave] = tk.BooleanVar(value=clave in seq_activos)
                    tk.Checkbutton(fila, text=label, variable=self._seq_vars[clave],
                        font=("Segoe UI", 10), bg="#ffffff", anchor='w').pack(
                        side='left', padx=8, pady=4, fill='x', expand=True)
                    btn_frame = tk.Frame(fila, bg="#ffffff")
                    btn_frame.pack(side='right', padx=4)
                    def _subir(i=idx):
                        if i > 0:
                            self._seq_orden[i], self._seq_orden[i-1] = self._seq_orden[i-1], self._seq_orden[i]
                            _render_seq()
                    def _bajar(i=idx):
                        if i < len(self._seq_orden) - 1:
                            self._seq_orden[i], self._seq_orden[i+1] = self._seq_orden[i+1], self._seq_orden[i]
                            _render_seq()
                    tk.Button(btn_frame, text="↑", font=("Segoe UI", 8), width=2, command=_subir).pack(side='left', padx=1)
                    tk.Button(btn_frame, text="↓", font=("Segoe UI", 8), width=2, command=_bajar).pack(side='left', padx=1)

            self._render_seq = _render_seq
            _render_seq()

        # ==================== PESTAÑA AVANZADO ====================
        tab_adv = ttk.Frame(notebook)
        notebook.add(tab_adv, text="⚙️ Avanzado")

        tk.Label(tab_adv, text="Ajustes del navegador y límites de seguridad para evitar bloqueos",
                 font=("Segoe UI", 9), fg="#555", bg="#f0f0f0").pack(anchor='w', padx=20, pady=(10, 0))

        self._seccion(tab_adv, "👤 Usar perfil existente de Facebook")
        tk.Label(tab_adv, text="Sí = usa tu sesión de Facebook guardada (no aplica a WhatsApp)",
                 font=("Segoe UI", 8), fg="gray", bg="#f0f0f0").pack(anchor='w', padx=20)
        self.var_usar_perfil = tk.StringVar(value=self._get('NAVEGADOR', 'usar_perfil_existente', 'si'))
        self._radio_si_no(tab_adv, self.var_usar_perfil)

        self._seccion(tab_adv, "🖥️ Maximizar ventana al iniciar")
        self.var_maximizar = tk.StringVar(value=self._get('NAVEGADOR', 'maximizar_ventana', 'si'))
        self._radio_si_no(tab_adv, self.var_maximizar)

        self._seccion(tab_adv, "⏰ Tiempo mínimo entre publicaciones (segundos)")
        tk.Label(tab_adv, text="Evita duplicados si se ejecuta 2 veces seguidas",
                 font=("Segoe UI", 8), fg="gray", bg="#f0f0f0").pack(anchor='w', padx=20)
        self.var_tiempo_minimo = tk.StringVar(value=self._get('LIMITES', 'tiempo_minimo_entre_publicaciones_segundos', '120'))
        tk.Spinbox(tab_adv, from_=30, to=600, textvariable=self.var_tiempo_minimo, width=8, font=("Segoe UI", 10)).pack(anchor='w', padx=20, pady=(0, 12))

        self._seccion(tab_adv, "🔓 Permitir forzar publicación manual")
        tk.Label(tab_adv, text="Sí = permite saltarse el tiempo mínimo en ejecución manual",
                 font=("Segoe UI", 8), fg="gray", bg="#f0f0f0").pack(anchor='w', padx=20)
        self.var_forzar_manual = tk.StringVar(value=self._get('LIMITES', 'permitir_forzar_publicacion_manual', 'si'))
        self._radio_si_no(tab_adv, self.var_forzar_manual)

        # Navegar a pestaña inicial si viene del panel
        if self.pestana_inicial == 'extractor':
            notebook.select(tab_pred)
        elif self.pestana_inicial == 'oraciones':
            notebook.select(tab_ora)
        elif self.pestana_inicial == 'correo':
            notebook.select(tab_correo)
        elif self.pestana_inicial == 'secuencia' and self.es_full:
            notebook.select(tab_seq)

        # ==================== BOTONES ====================
        frame_botones = tk.Frame(self.root, bg="#f0f0f0", pady=8)
        frame_botones.pack(fill='x', padx=10)

        tk.Button(frame_botones, text="❌ Cancelar", font=("Segoe UI", 10), bg="#e0e0e0",
                  width=14, command=self.root.destroy).pack(side='right', padx=5)

        tk.Button(frame_botones, text="💾 Guardar", font=("Segoe UI", 10, "bold"),
                  bg="#1a73e8", fg="white", width=14, command=self._guardar_config).pack(side='right', padx=5)

    def _construir_tab_correo(self, tab):
        estado = 'normal' if self.es_full else 'disabled'
        config_correo = leer_config_correo()

        tk.Label(tab, text="Envía mensajes bíblicos y prédicas por correo a tu lista de destinatarios",
                 font=("Segoe UI", 9), fg="#555", bg="#f0f0f0").pack(anchor='w', padx=20, pady=(10, 0))

        if not self.es_full:
            banner = tk.Frame(tab, bg="#fff3cd", pady=6)
            banner.pack(fill='x', padx=20, pady=(8, 0))
            tk.Label(banner, text="🔒 Estas funciones están disponibles en la versión Completa",
                     font=("Segoe UI", 9, "bold"), fg="#856404", bg="#fff3cd").pack()

        self._seccion(tab, "📧 Cuenta que envía los correos")
        self.var_correo_proveedor = tk.StringVar(value=config_correo['proveedor'])
        self.var_correo_servidor = tk.StringVar(value=config_correo['servidor'])
        self.var_correo_puerto = tk.StringVar(value=str(config_correo['puerto']))
        self.var_correo_remitente = tk.StringVar(value=config_correo['remitente'])
        self.var_correo_nombre = tk.StringVar(value=config_correo['nombre_remitente'])
        self.var_correo_asunto = tk.StringVar(value=config_correo['asunto'])
        self.var_correo_contrasena = tk.StringVar()
        self.var_correo_biblicos = tk.BooleanVar(value=config_correo['enviar_biblicos'])
        self.var_correo_predicas = tk.BooleanVar(value=config_correo['enviar_predicas'])

        def al_cambiar_proveedor():
            proveedor = self.var_correo_proveedor.get()
            if proveedor != 'otro':
                _, servidor, puerto, _ = PROVEEDORES[proveedor]
                self.var_correo_servidor.set(servidor)
                self.var_correo_puerto.set(str(puerto))

        fila_prov = tk.Frame(tab, bg="#f0f0f0")
        fila_prov.pack(anchor='w', padx=20)
        for clave, (nombre, _, _, _) in PROVEEDORES.items():
            tk.Radiobutton(fila_prov, text=nombre, variable=self.var_correo_proveedor, value=clave, bg="#f0f0f0",
                           font=("Segoe UI", 10), state=estado, command=al_cambiar_proveedor).pack(side='left', padx=(0, 12))

        datos = tk.Frame(tab, bg="#f0f0f0")
        datos.pack(anchor='w', padx=20, pady=(6, 0))
        tiene_contrasena = bool(leer_contrasena()) if self.es_full else False
        filas = [
            ("Correo:", self.var_correo_remitente, None),
            ("Nombre que verán:", self.var_correo_nombre, None),
            ("Contraseña de aplicación:", self.var_correo_contrasena, '•'),
            ("Asunto:", self.var_correo_asunto, None),
        ]
        for i, (texto, variable, oculto) in enumerate(filas):
            tk.Label(datos, text=texto, font=("Segoe UI", 9), bg="#f0f0f0").grid(row=i, column=0, sticky='w', pady=2)
            tk.Entry(datos, textvariable=variable, width=38, font=("Segoe UI", 10), show=oculto or '',
                     state=estado).grid(row=i, column=1, sticky='w', padx=(8, 0), pady=2)
        tk.Label(datos, text="✅ guardada en Windows (escribe otra solo para cambiarla)" if tiene_contrasena
                 else "Se guarda cifrada en Windows. En Gmail se crea en myaccount.google.com/apppasswords",
                 font=("Segoe UI", 8), fg="#28a745" if tiene_contrasena else "gray", bg="#f0f0f0",
                 wraplength=330, justify='left').grid(row=5, column=1, sticky='w', padx=(8, 0))
        tk.Label(datos, text="{titulo} = primera línea del mensaje", font=("Segoe UI", 8), fg="gray",
                 bg="#f0f0f0").grid(row=6, column=1, sticky='w', padx=(8, 0))

        fila_srv = tk.Frame(tab, bg="#f0f0f0")
        fila_srv.pack(anchor='w', padx=20, pady=(6, 0))
        tk.Label(fila_srv, text="Servidor:", font=("Segoe UI", 9), bg="#f0f0f0").pack(side='left')
        tk.Entry(fila_srv, textvariable=self.var_correo_servidor, width=26, font=("Segoe UI", 9),
                 state=estado).pack(side='left', padx=(6, 12))
        tk.Label(fila_srv, text="Puerto:", font=("Segoe UI", 9), bg="#f0f0f0").pack(side='left')
        tk.Entry(fila_srv, textvariable=self.var_correo_puerto, width=6, font=("Segoe UI", 9),
                 state=estado).pack(side='left', padx=(6, 0))

        self._seccion(tab, "📦 Qué enviar por correo")
        fila_contenido = tk.Frame(tab, bg="#f0f0f0")
        fila_contenido.pack(anchor='w', padx=20)
        tk.Checkbutton(fila_contenido, text="📖 Mensajes bíblicos", variable=self.var_correo_biblicos, bg="#f0f0f0",
                       font=("Segoe UI", 10), state=estado).pack(side='left', padx=(0, 15))
        tk.Checkbutton(fila_contenido, text="🎬 Prédicas extraídas", variable=self.var_correo_predicas, bg="#f0f0f0",
                       font=("Segoe UI", 10), state=estado).pack(side='left')
        tk.Label(tab, text="Envía lo mismo que se publicó en Facebook en esa ejecución. Si no se publicó nada, "
                           "elige un mensaje y la siguiente prédica aún no enviada (sin quitársela a Facebook)",
                 font=("Segoe UI", 8), fg="gray", bg="#f0f0f0", wraplength=620, justify='left').pack(anchor='w', padx=20)

        def probar():
            proveedor = self.var_correo_proveedor.get()
            seguridad = PROVEEDORES.get(proveedor, PROVEEDORES['otro'])[3] if proveedor != 'otro' \
                else leer_config_correo()['seguridad']
            try:
                puerto = int(self.var_correo_puerto.get())
            except ValueError:
                messagebox.showerror("❌ Correo", "El puerto debe ser un número", parent=self.root)
                return
            config = {
                'servidor': self.var_correo_servidor.get().strip(), 'puerto': puerto, 'seguridad': seguridad,
                'remitente': self.var_correo_remitente.get().strip(), 'nombre_remitente': self.var_correo_nombre.get().strip(),
            }
            contrasena = self.var_correo_contrasena.get().replace(' ', '') or leer_contrasena()
            if not config['remitente'] or not contrasena:
                messagebox.showerror("❌ Correo", "Escribe el correo y la contraseña de aplicación", parent=self.root)
                return
            if '@' not in config['remitente']:
                messagebox.showerror("❌ Correo", "Escribe el correo completo, por ejemplo nombre@gmail.com", parent=self.root)
                return
            self.root.config(cursor='wait')
            self.root.update()
            ok, mensaje = probar_conexion(config, contrasena)
            self.root.config(cursor='')
            (messagebox.showinfo if ok else messagebox.showerror)("✉️ Prueba de correo", mensaje, parent=self.root)

        botones = tk.Frame(tab, bg="#f0f0f0")
        botones.pack(fill='x', padx=20, pady=(10, 0))
        tk.Button(botones, text="🧪  Probar conexión", font=("Segoe UI", 10, "bold"),
                  bg="#17a2b8" if self.es_full else "#e0e0e0", fg="white" if self.es_full else "#9e9e9e",
                  state=estado, command=probar).pack(side='left', fill='x', expand=True, padx=(0, 6), ipady=4)
        tk.Button(botones, text="👥  Destinatarios de correo", font=("Segoe UI", 10, "bold"),
                  bg="#1a73e8" if self.es_full else "#e0e0e0", fg="white" if self.es_full else "#9e9e9e",
                  state=estado, command=self._abrir_gestor_destinatarios_correo).pack(side='left', fill='x', expand=True, ipady=4)

    def _abrir_gestor_destinatarios_correo(self):
        ventana = tk.Toplevel(self.root)
        ventana.withdraw()
        ventana.title("👥 Destinatarios de correo")
        ventana.resizable(False, False)
        ventana.configure(bg="#f0f0f0")
        ventana.transient(self.root)

        header = tk.Frame(ventana, bg="#1a73e8", pady=12)
        header.pack(fill='x')
        tk.Label(header, text="👥 Destinatarios de correo",
                 font=("Segoe UI", 12, "bold"), bg="#1a73e8", fg="white").pack()
        tk.Label(header, text="✅ = recibe por defecto · Doble clic para cambiarlo · Editar para corregir un correo",
                 font=("Segoe UI", 8), bg="#1a73e8", fg="#cce0ff").pack()

        frame = tk.Frame(ventana, bg="#f0f0f0", padx=20, pady=10)
        frame.pack(fill='both', expand=True)

        var_email = tk.StringVar()
        var_nombre = tk.StringVar()
        fila_nueva = tk.Frame(frame, bg="#f0f0f0")
        fila_nueva.pack(fill='x', pady=(0, 8))
        tk.Label(fila_nueva, text="Correo:", font=("Segoe UI", 9), bg="#f0f0f0").grid(row=0, column=0, sticky='w')
        entrada_email = tk.Entry(fila_nueva, textvariable=var_email, width=26, font=("Segoe UI", 10))
        entrada_email.grid(row=0, column=1, padx=(6, 0), pady=2)
        tk.Label(fila_nueva, text="Nombre:", font=("Segoe UI", 9), bg="#f0f0f0").grid(row=1, column=0, sticky='w')
        tk.Entry(fila_nueva, textvariable=var_nombre, width=26, font=("Segoe UI", 10)).grid(row=1, column=1, padx=(6, 0), pady=2)

        frame_lista = tk.Frame(frame, bg="#f0f0f0")
        frame_lista.pack(fill='both', expand=True)
        scrollbar = tk.Scrollbar(frame_lista)
        scrollbar.pack(side='right', fill='y')
        lista = tk.Listbox(frame_lista, yscrollcommand=scrollbar.set,
                           font=("Segoe UI", 10), height=9, bg="white", relief='solid', borderwidth=1)
        lista.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=lista.yview)

        destinatarios = leer_destinatarios_correo()
        estado = {'editando': None}

        def cargar():
            lista.delete(0, tk.END)
            for d in destinatarios:
                marca = "✅" if d.get('seleccionado', True) else "⬜"
                nombre = f" — {d['nombre']}" if d.get('nombre') else ""
                lista.insert(tk.END, f"{marca} {d['email']}{nombre}")

        def guardar():
            try:
                guardar_destinatarios_correo(destinatarios)
            except Exception as e:
                messagebox.showerror("❌ Error", f"No se pudo guardar: {e}", parent=ventana)

        def limpiar_campos():
            estado['editando'] = None
            boton_agregar.config(text="+ Agregar")
            var_email.set('')
            var_nombre.set('')
            entrada_email.focus_set()

        def agregar():
            email = var_email.get().strip().lower()
            if '@' not in email or '.' not in email.split('@')[-1] or ' ' in email:
                messagebox.showwarning("⚠️ Aviso", "Escribe un correo válido", parent=ventana)
                return
            editando = estado['editando']
            if any(d['email'] == email for i, d in enumerate(destinatarios) if i != editando):
                messagebox.showwarning("⚠️ Aviso", "Ese correo ya está en la lista", parent=ventana)
                return
            if editando is None:
                destinatarios.append({'email': email, 'nombre': var_nombre.get().strip(), 'seleccionado': True})
            else:
                destinatarios[editando]['email'] = email
                destinatarios[editando]['nombre'] = var_nombre.get().strip()
            guardar()
            cargar()
            limpiar_campos()

        def editar():
            sel = lista.curselection()
            if not sel:
                messagebox.showinfo("ℹ️ Destinatarios", "Primero haz clic en un correo de la lista", parent=ventana)
                return
            estado['editando'] = sel[0]
            var_email.set(destinatarios[sel[0]]['email'])
            var_nombre.set(destinatarios[sel[0]].get('nombre', ''))
            boton_agregar.config(text="💾 Guardar")
            entrada_email.focus_set()

        def alternar(event=None):
            sel = lista.curselection()
            if not sel and event is None:
                messagebox.showinfo("ℹ️ Destinatarios", "Primero haz clic en un correo de la lista", parent=ventana)
            if sel:
                d = destinatarios[sel[0]]
                d['seleccionado'] = not d.get('seleccionado', True)
                guardar()
                cargar()
                lista.selection_set(sel[0])

        def eliminar():
            sel = lista.curselection()
            if not sel:
                messagebox.showwarning("⚠️ Aviso", "Selecciona un correo para eliminar", parent=ventana)
                return
            if messagebox.askyesno("🗑️ Confirmar", f"¿Eliminar '{destinatarios[sel[0]]['email']}'?", parent=ventana):
                destinatarios.pop(sel[0])
                guardar()
                cargar()
                limpiar_campos()

        def cerrar():
            ventana.grab_release()
            ventana.destroy()

        boton_agregar = tk.Button(fila_nueva, text="+ Agregar", font=("Segoe UI", 10, "bold"), bg="#1a73e8", fg="white",
                                  command=agregar, width=10)
        boton_agregar.grid(row=0, column=2, rowspan=2, padx=(10, 0), sticky='ns')
        lista.bind('<Double-Button-1>', alternar)
        entrada_email.bind('<Return>', lambda e: agregar())

        frame_btns = tk.Frame(frame, bg="#f0f0f0")
        frame_btns.pack(fill='x', pady=(8, 0))
        tk.Button(frame_btns, text="✅/⬜ Por defecto", font=("Segoe UI", 10), bg="#17a2b8", fg="white",
                  command=alternar, width=16).pack(side='left', padx=(0, 5), ipady=4)
        tk.Button(frame_btns, text="Editar", font=("Segoe UI", 10), bg="#ffc107",
                  command=editar, width=9).pack(side='left', padx=(0, 5), ipady=4)
        tk.Button(frame_btns, text="Eliminar", font=("Segoe UI", 10), bg="#dc3545", fg="white",
                  command=eliminar, width=9).pack(side='left', ipady=4)
        tk.Button(frame_btns, text="Cerrar", font=("Segoe UI", 10), bg="#6c757d", fg="white",
                  command=cerrar, width=10).pack(side='right', ipady=4)
        ventana.protocol("WM_DELETE_WINDOW", cerrar)

        cargar()
        ventana.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - 260
        y = (self.root.winfo_screenheight() // 2) - 230
        ventana.geometry(f'520x460+{x}+{y}')
        ventana.deiconify()
        ventana.grab_set()
        entrada_email.focus_set()

    def _abrir_gestor_grupos(self):
        ventana = tk.Toplevel(self.root)
        ventana.withdraw()
        ventana.title("👥 Grupos y contactos - Oraciones")
        ventana.resizable(False, False)
        ventana.configure(bg="#f0f0f0")
        ventana.transient(self.root)
        ventana.grab_set()

        header = tk.Frame(ventana, bg="#1a73e8", pady=12)
        header.pack(fill='x')
        tk.Label(header, text="👥 Grupos y contactos para oraciones",
                 font=("Segoe UI", 12, "bold"), bg="#1a73e8", fg="white").pack()
        tk.Label(header, text="El nombre debe ser EXACTAMENTE igual a como aparece en WhatsApp",
                 font=("Segoe UI", 8), bg="#1a73e8", fg="#cce0ff").pack()

        frame = tk.Frame(ventana, bg="#f0f0f0", padx=20, pady=10)
        frame.pack(fill='both', expand=True)

        frame_lista = tk.Frame(frame, bg="#f0f0f0")
        frame_lista.pack(fill='both', expand=True)

        scrollbar = tk.Scrollbar(frame_lista)
        scrollbar.pack(side='right', fill='y')

        lista = tk.Listbox(frame_lista, yscrollcommand=scrollbar.set,
                           font=("Segoe UI", 10), height=8, bg="white", relief='solid', borderwidth=1)
        lista.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=lista.yview)

        def cargar():
            lista.delete(0, tk.END)
            try:
                if os.path.exists(self.archivo_grupos):
                    with open(self.archivo_grupos, 'r', encoding='utf-8') as f:
                        datos = json.load(f)
                    for g in datos.get('grupos', []):
                        icono = "👥" if g.get('tipo') == 'grupo' else "👤"
                        estado = "✅" if g.get('activo', True) else "❌"
                        lista.insert(tk.END, f"{estado} {icono} {g['nombre']} ({g.get('tipo','grupo')})")
            except Exception as e:
                messagebox.showerror("❌ Error", f"Error cargando grupos: {e}")

        frame_btns = tk.Frame(frame, bg="#f0f0f0")
        frame_btns.pack(fill='x', pady=(8, 0))

        def agregar():
            self._agregar_grupo_en(ventana, cargar)

        def editar():
            sel = lista.curselection()
            if not sel:
                messagebox.showwarning("⚠️ Aviso", "Selecciona un grupo para editar")
                return
            self._editar_grupo_en(sel[0], ventana, cargar)

        def eliminar():
            sel = lista.curselection()
            if not sel:
                messagebox.showwarning("⚠️ Aviso", "Selecciona un grupo para eliminar")
                return
            idx = sel[0]
            try:
                with open(self.archivo_grupos, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                nombre = datos['grupos'][idx]['nombre']
                if not messagebox.askyesno("🗑️ Confirmar", f"¿Eliminar '{nombre}'?"):
                    return
                datos['grupos'].pop(idx)
                with open(self.archivo_grupos, 'w', encoding='utf-8') as f:
                    json.dump(datos, f, ensure_ascii=False, indent=2)
                cargar()
            except Exception as e:
                messagebox.showerror("❌ Error", f"Error eliminando: {e}")

        tk.Button(frame_btns, text="+ Agregar", font=("Segoe UI", 10, "bold"),
                  bg="#1a73e8", fg="white", command=agregar, width=12).pack(side='left', padx=(0, 5), ipady=4)
        tk.Button(frame_btns, text="Editar", font=("Segoe UI", 10),
                  bg="#ffc107", command=editar, width=10).pack(side='left', padx=(0, 5), ipady=4)
        tk.Button(frame_btns, text="Eliminar", font=("Segoe UI", 10),
                  bg="#dc3545", fg="white", command=eliminar, width=10).pack(side='left', padx=(0, 5), ipady=4)
        tk.Button(frame_btns, text="Cerrar", font=("Segoe UI", 10),
                  bg="#6c757d", fg="white", command=ventana.destroy, width=10).pack(side='right', ipady=4)

        cargar()
        x = (self.root.winfo_screenwidth() // 2) - 220
        y = (self.root.winfo_screenheight() // 2) - 200
        ventana.geometry(f'440x380+{x}+{y}')
        ventana.deiconify()

    def _agregar_grupo_en(self, parent, callback_refresh):
        v = tk.Toplevel(parent)
        v.withdraw()
        v.title("✚ Agregar grupo/contacto")
        v.resizable(False, False)
        v.configure(bg="#f0f0f0")
        v.transient(parent)
        v.grab_set()

        tk.Label(v, text="Nombre (igual que en WhatsApp):", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', padx=20, pady=(20, 3))
        var_nombre = tk.StringVar()
        tk.Entry(v, textvariable=var_nombre, width=40, font=("Segoe UI", 10)).pack(anchor='w', padx=20)

        tk.Label(v, text="Tipo:", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', padx=20, pady=(10, 3))
        var_tipo = tk.StringVar(value="grupo")
        f = tk.Frame(v, bg="#f0f0f0")
        f.pack(anchor='w', padx=20)
        tk.Radiobutton(f, text="Grupo", variable=var_tipo, value="grupo", bg="#f0f0f0").pack(side='left', padx=(0, 10))
        tk.Radiobutton(f, text="Contacto", variable=var_tipo, value="contacto", bg="#f0f0f0").pack(side='left')

        def guardar():
            nombre = var_nombre.get().strip()
            if not nombre:
                messagebox.showerror("Error", "El nombre no puede estar vacío")
                return
            self._guardar_grupo_nuevo(nombre, var_tipo.get())
            callback_refresh()
            v.destroy()

        fb = tk.Frame(v, bg="#f0f0f0")
        fb.pack(fill='x', padx=20, pady=20)
        tk.Button(fb, text="Cancelar", font=("Segoe UI", 10), bg="#e0e0e0", command=v.destroy, width=10).pack(side='left')
        tk.Button(fb, text="✚ Agregar", font=("Segoe UI", 10, "bold"), bg="#1a73e8", fg="white", command=guardar, width=12).pack(side='right')

        v.geometry(f'400x260+{(v.winfo_screenwidth()//2)-200}+{(v.winfo_screenheight()//2)-130}')
        v.deiconify()

    def _editar_grupo_en(self, idx, parent, callback_refresh):
        try:
            with open(self.archivo_grupos, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            grupo = datos['grupos'][idx]
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error leyendo grupos: {e}")
            return

        v = tk.Toplevel(parent)
        v.withdraw()
        v.title("✏️ Editar grupo/contacto")
        v.resizable(False, False)
        v.configure(bg="#f0f0f0")
        v.transient(parent)
        v.grab_set()

        tk.Label(v, text="Nombre (igual que en WhatsApp):", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', padx=20, pady=(20, 3))
        var_nombre = tk.StringVar(value=grupo.get('nombre', ''))
        tk.Entry(v, textvariable=var_nombre, width=40, font=("Segoe UI", 10)).pack(anchor='w', padx=20)

        tk.Label(v, text="Tipo:", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', padx=20, pady=(10, 3))
        var_tipo = tk.StringVar(value=grupo.get('tipo', 'grupo'))
        f = tk.Frame(v, bg="#f0f0f0")
        f.pack(anchor='w', padx=20)
        tk.Radiobutton(f, text="Grupo", variable=var_tipo, value="grupo", bg="#f0f0f0").pack(side='left', padx=(0, 10))
        tk.Radiobutton(f, text="Contacto", variable=var_tipo, value="contacto", bg="#f0f0f0").pack(side='left')

        def guardar():
            nombre = var_nombre.get().strip()
            if not nombre:
                messagebox.showerror("Error", "El nombre no puede estar vacío")
                return
            datos['grupos'][idx] = {'nombre': nombre, 'tipo': var_tipo.get(), 'activo': True}
            try:
                with open(self.archivo_grupos, 'w', encoding='utf-8') as f2:
                    json.dump(datos, f2, ensure_ascii=False, indent=2)
                callback_refresh()
                v.destroy()
            except Exception as e:
                messagebox.showerror("❌ Error", f"Error guardando: {e}")

        fb = tk.Frame(v, bg="#f0f0f0")
        fb.pack(fill='x', padx=20, pady=20)
        tk.Button(fb, text="Cancelar", font=("Segoe UI", 10), bg="#e0e0e0", command=v.destroy, width=10).pack(side='left')
        tk.Button(fb, text="💾 Guardar", font=("Segoe UI", 10, "bold"), bg="#1a73e8", fg="white", command=guardar, width=12).pack(side='right')

        v.geometry(f'400x260+{(v.winfo_screenwidth()//2)-200}+{(v.winfo_screenheight()//2)-130}')
        v.deiconify()

    def _abrir_gestor_mensajes_oracion(self):
        ventana = tk.Toplevel(self.root)
        ventana.withdraw()
        ventana.title("📝 Mensajes de oración")
        ventana.resizable(False, False)
        ventana.configure(bg="#f0f0f0")
        ventana.transient(self.root)
        ventana.grab_set()

        header = tk.Frame(ventana, bg="#28a745", pady=12)
        header.pack(fill='x')
        tk.Label(header, text="📝 Mensajes de oración", font=("Segoe UI", 12, "bold"), bg="#28a745", fg="white").pack()
        tk.Label(header, text="Un mensaje por línea en cada sección", font=("Segoe UI", 8), bg="#28a745", fg="#ccffdd").pack()

        frame = tk.Frame(ventana, bg="#f0f0f0", padx=20, pady=10)
        frame.pack(fill='both', expand=True)

        tk.Label(frame, text="Para GRUPOS:", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w')
        tk.Label(frame, text="Se envía a grupos de WhatsApp", font=("Segoe UI", 8), fg="gray", bg="#f0f0f0").pack(anchor='w')

        frame_g = tk.Frame(frame, bg="#f0f0f0")
        frame_g.pack(fill='both', expand=True, pady=(3, 8))
        scroll_g = tk.Scrollbar(frame_g)
        scroll_g.pack(side='right', fill='y')
        lista_grupos_msg = tk.Listbox(frame_g, yscrollcommand=scroll_g.set, font=("Segoe UI", 9), height=5, bg="white", relief='solid', borderwidth=1, selectmode='single')
        lista_grupos_msg.pack(side='left', fill='both', expand=True)
        scroll_g.config(command=lista_grupos_msg.yview)

        frame_btn_g = tk.Frame(frame, bg="#f0f0f0")
        frame_btn_g.pack(fill='x', pady=(0, 10))

        tk.Label(frame, text="Para INDIVIDUALES:", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w')
        tk.Label(frame, text="Se envía a contactos individuales", font=("Segoe UI", 8), fg="gray", bg="#f0f0f0").pack(anchor='w')

        frame_i = tk.Frame(frame, bg="#f0f0f0")
        frame_i.pack(fill='both', expand=True, pady=(3, 8))
        scroll_i = tk.Scrollbar(frame_i)
        scroll_i.pack(side='right', fill='y')
        lista_ind_msg = tk.Listbox(frame_i, yscrollcommand=scroll_i.set, font=("Segoe UI", 9), height=5, bg="white", relief='solid', borderwidth=1, selectmode='single')
        lista_ind_msg.pack(side='left', fill='both', expand=True)
        scroll_i.config(command=lista_ind_msg.yview)

        frame_btn_i = tk.Frame(frame, bg="#f0f0f0")
        frame_btn_i.pack(fill='x', pady=(0, 5))

        archivo_msg = os.path.join(self.base_dir, "llamados-oracion", "mensajes_oracion.txt")

        def cargar_mensajes():
            lista_grupos_msg.delete(0, tk.END)
            lista_ind_msg.delete(0, tk.END)
            if not os.path.exists(archivo_msg):
                # Crear archivo con mensajes por defecto
                os.makedirs(os.path.dirname(archivo_msg), exist_ok=True)
                with open(archivo_msg, 'w', encoding='utf-8') as f:
                    f.write(
                        "[GRUPOS]\n"
                        "🙏 Hermanos, tomemos un momento para orar juntos. ¡Los invito a elevar una oración!\n"
                        "🙏 Familia, detengámonos un instante para orar. ¡El Señor nos escucha!\n\n"
                        "[INDIVIDUALES]\n"
                        "🙏 Hola, te invito a un momento de oración. ¡Oremos juntos!\n"
                        "🙏 Amigo/a, ¿podemos orar juntos un momento? ¡Dios tiene algo para ti hoy!\n"
                    )
            with open(archivo_msg, 'r', encoding='utf-8') as f:
                contenido = f.read()
            if '[GRUPOS]' in contenido and '[INDIVIDUALES]' in contenido:
                partes = contenido.split('[INDIVIDUALES]')
                for linea in partes[0].replace('[GRUPOS]', '').strip().split('\n'):
                    if linea.strip():
                        lista_grupos_msg.insert(tk.END, linea.strip())
                for linea in partes[1].strip().split('\n'):
                    if linea.strip():
                        lista_ind_msg.insert(tk.END, linea.strip())

        def _guardar_en_archivo():
            grupos = list(lista_grupos_msg.get(0, tk.END))
            inds = list(lista_ind_msg.get(0, tk.END))
            if not grupos and not inds:
                return
            contenido = "[GRUPOS]\n" + "\n".join(grupos) + "\n\n[INDIVIDUALES]\n" + "\n".join(inds) + "\n"
            os.makedirs(os.path.dirname(archivo_msg), exist_ok=True)
            with open(archivo_msg, 'w', encoding='utf-8') as f:
                f.write(contenido)

        def agregar_msg(lista):
            v = tk.Toplevel(ventana)
            v.withdraw()
            v.title("✚ Nuevo mensaje")
            v.resizable(False, False)
            v.configure(bg="#f0f0f0")
            v.transient(ventana)
            v.grab_set()
            tk.Label(v, text="Texto del mensaje:", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', padx=20, pady=(20, 3))
            txt = tk.Text(v, font=("Segoe UI", 10), height=4, width=45, relief='solid', borderwidth=1)
            txt.pack(padx=20)
            def confirmar():
                texto = txt.get('1.0', tk.END).strip()
                if not texto:
                    return
                lista.insert(tk.END, texto)
                _guardar_en_archivo()
                v.destroy()
            fb = tk.Frame(v, bg="#f0f0f0")
            fb.pack(fill='x', padx=20, pady=15)
            tk.Button(fb, text="Cancelar", bg="#e0e0e0", font=("Segoe UI", 10), command=v.destroy, width=10).pack(side='left')
            tk.Button(fb, text="✚ Agregar", bg="#1a73e8", fg="white", font=("Segoe UI", 10, "bold"), command=confirmar, width=12).pack(side='right')
            v.geometry(f'420x220+{(v.winfo_screenwidth()//2)-210}+{(v.winfo_screenheight()//2)-110}')
            v.deiconify()

        def editar_msg(lista):
            sel = lista.curselection()
            if not sel:
                messagebox.showwarning("⚠️ Aviso", "Selecciona un mensaje para editar")
                return
            idx = sel[0]
            texto_actual = lista.get(idx)
            v = tk.Toplevel(ventana)
            v.withdraw()
            v.title("✏️ Editar mensaje")
            v.resizable(False, False)
            v.configure(bg="#f0f0f0")
            v.transient(ventana)
            v.grab_set()
            tk.Label(v, text="Texto del mensaje:", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', padx=20, pady=(20, 3))
            txt = tk.Text(v, font=("Segoe UI", 10), height=4, width=45, relief='solid', borderwidth=1)
            txt.insert('1.0', texto_actual)
            txt.pack(padx=20)
            def confirmar():
                texto = txt.get('1.0', tk.END).strip()
                if not texto:
                    return
                lista.delete(idx)
                lista.insert(idx, texto)
                _guardar_en_archivo()
                v.destroy()
            fb = tk.Frame(v, bg="#f0f0f0")
            fb.pack(fill='x', padx=20, pady=15)
            tk.Button(fb, text="Cancelar", bg="#e0e0e0", font=("Segoe UI", 10), command=v.destroy, width=10).pack(side='left')
            tk.Button(fb, text="💾 Guardar", bg="#1a73e8", fg="white", font=("Segoe UI", 10, "bold"), command=confirmar, width=12).pack(side='right')
            v.geometry(f'420x220+{(v.winfo_screenwidth()//2)-210}+{(v.winfo_screenheight()//2)-110}')
            v.deiconify()

        def eliminar_msg(lista):
            sel = lista.curselection()
            if not sel:
                messagebox.showwarning("⚠️ Aviso", "Selecciona un mensaje para eliminar")
                return
            if messagebox.askyesno("🗑️ Confirmar", "¿Eliminar este mensaje?"):
                lista.delete(sel[0])
                _guardar_en_archivo()

        tk.Button(frame_btn_g, text="✚ Agregar", font=("Segoe UI", 9, "bold"), bg="#1a73e8", fg="white", command=lambda: agregar_msg(lista_grupos_msg)).pack(side='left', padx=(0, 5), ipady=3)
        tk.Button(frame_btn_g, text="✏️ Editar", font=("Segoe UI", 9), bg="#ffc107", command=lambda: editar_msg(lista_grupos_msg)).pack(side='left', padx=(0, 5), ipady=3)
        tk.Button(frame_btn_g, text="🗑️ Eliminar", font=("Segoe UI", 9), bg="#dc3545", fg="white", command=lambda: eliminar_msg(lista_grupos_msg)).pack(side='left', ipady=3)

        tk.Button(frame_btn_i, text="✚ Agregar", font=("Segoe UI", 9, "bold"), bg="#1a73e8", fg="white", command=lambda: agregar_msg(lista_ind_msg)).pack(side='left', padx=(0, 5), ipady=3)
        tk.Button(frame_btn_i, text="✏️ Editar", font=("Segoe UI", 9), bg="#ffc107", command=lambda: editar_msg(lista_ind_msg)).pack(side='left', padx=(0, 5), ipady=3)
        tk.Button(frame_btn_i, text="🗑️ Eliminar", font=("Segoe UI", 9), bg="#dc3545", fg="white", command=lambda: eliminar_msg(lista_ind_msg)).pack(side='left', ipady=3)

        frame_footer = tk.Frame(ventana, bg="#f0f0f0")
        frame_footer.pack(fill='x', padx=20, pady=(0, 15))
        tk.Button(frame_footer, text="Cerrar", font=("Segoe UI", 10),
                  bg="#6c757d", fg="white", command=lambda: [ventana.grab_release(), ventana.destroy()], width=20).pack(ipady=4)

        ventana.protocol("WM_DELETE_WINDOW", lambda: [ventana.grab_release(), ventana.destroy()])
        cargar_mensajes()
        x = (self.root.winfo_screenwidth() // 2) - 240
        y = (self.root.winfo_screenheight() // 2) - 300
        ventana.geometry(f'480x580+{x}+{y}')
        ventana.deiconify()

    def _nombre_corto(self, nombre, maximo=17):
        """Acorta nombres largos solo para mostrarlos; el nombre completo se usa al enviar"""
        return nombre if len(nombre) <= maximo else nombre[:maximo].rstrip() + "…"

    def _abrir_selector_destinatarios(self):
        """Panel para marcar qué grupos/contactos reciben oraciones por defecto"""
        import json

        ventana = tk.Toplevel(self.root)
        ventana.withdraw()
        ventana.title("✅ Destinatarios por defecto")
        ventana.resizable(False, False)
        ventana.configure(bg="#f0f0f0")
        ventana.transient(self.root)
        ventana.grab_set()

        header = tk.Frame(ventana, bg="#17a2b8", pady=12)
        header.pack(fill='x')
        tk.Label(header, text="✅ Destinatarios por defecto",
                 font=("Segoe UI", 12, "bold"), bg="#17a2b8", fg="white").pack()
        tk.Label(header, text="Marca quiénes recibirán oraciones al ejecutar automáticamente",
                 font=("Segoe UI", 8), bg="#17a2b8", fg="#d0f5ff").pack()

        frame = tk.Frame(ventana, bg="#f0f0f0", padx=20, pady=10)
        frame.pack(fill='both', expand=True)

        # Cargar grupos
        grupos = []
        if os.path.exists(self.archivo_grupos):
            try:
                with open(self.archivo_grupos, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                grupos = datos.get('grupos', [])
            except:
                pass

        if not grupos:
            tk.Label(frame, text="No hay grupos/contactos registrados.\nAgrega primero en 'Gestionar grupos y contactos'.",
                     font=("Segoe UI", 10), bg="#f0f0f0", fg="#555", justify='center').pack(pady=20)
        else:
            vars_sel = []

            # Seleccionar todos
            var_todos = tk.BooleanVar()
            def toggle_todos():
                for v in vars_sel:
                    v.set(var_todos.get())
            tk.Checkbutton(frame, text="Seleccionar todos", variable=var_todos,
                           command=toggle_todos, font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', pady=(0,4))
            tk.Frame(frame, bg="#ccc", height=1).pack(fill='x', pady=(0, 8))

            # Frame con scroll
            canvas = tk.Canvas(frame, bg="#f0f0f0", highlightthickness=0, height=200)
            scroll = tk.Scrollbar(frame, orient='vertical', command=canvas.yview)
            frame_scroll = tk.Frame(canvas, bg="#f0f0f0")
            frame_scroll.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
            canvas.create_window((0, 0), window=frame_scroll, anchor='nw')
            canvas.configure(yscrollcommand=scroll.set)
            canvas.pack(side='left', fill='both', expand=True)
            scroll.pack(side='right', fill='y')

            # Cargar mensajes disponibles para el dropdown
            mensajes_grupos_lista = []
            mensajes_ind_lista = []
            archivo_msg = os.path.join(self.base_dir, "llamados-oracion", "mensajes_oracion.txt")
            if os.path.exists(archivo_msg):
                with open(archivo_msg, 'r', encoding='utf-8') as f:
                    contenido_msg = f.read()
                if '[GRUPOS]' in contenido_msg and '[INDIVIDUALES]' in contenido_msg:
                    partes = contenido_msg.split('[INDIVIDUALES]')
                    mensajes_grupos_lista = [l.strip() for l in partes[0].replace('[GRUPOS]', '').strip().split('\n') if l.strip()]
                    mensajes_ind_lista = [l.strip() for l in partes[1].strip().split('\n') if l.strip()]
                else:
                    todas = [l.strip() for l in contenido_msg.split('\n') if l.strip() and not l.startswith('[')]
                    mensajes_grupos_lista = todas
                    mensajes_ind_lista = todas

            vars_msg = []

            for g in grupos:
                seleccionado = g.get('seleccionado', True)
                var = tk.BooleanVar(value=seleccionado)
                vars_sel.append(var)
                icono = "👥" if g.get('tipo') == 'grupo' else "👤"

                # Mensajes disponibles según tipo
                msgs_disponibles = mensajes_grupos_lista if g.get('tipo') == 'grupo' else mensajes_ind_lista
                opciones = ["🎲 Aleatorio"] + msgs_disponibles

                # Valor guardado
                msg_guardado = g.get('mensaje_asignado', None)
                val_inicial = msg_guardado if msg_guardado and msg_guardado in msgs_disponibles else "🎲 Aleatorio"
                var_msg = tk.StringVar(value=val_inicial)
                vars_msg.append(var_msg)

                fila = tk.Frame(frame_scroll, bg="#f0f0f0")
                fila.pack(fill='x', pady=3)

                tk.Checkbutton(fila,
                               text=f"{icono} {self._nombre_corto(g['nombre'])}",
                               variable=var, bg="#f0f0f0",
                               font=("Segoe UI", 10), width=20, anchor='w').pack(side='left')

                cb = ttk.Combobox(fila, textvariable=var_msg,
                                  values=opciones, state='readonly',
                                  width=30, font=("Segoe UI", 8))
                cb.pack(side='left', padx=(5, 0))

            def actualizar_todos(*args):
                var_todos.set(all(v.get() for v in vars_sel))
            for v in vars_sel:
                v.trace_add('write', actualizar_todos)
            actualizar_todos()

            def guardar_seleccion():
                try:
                    with open(self.archivo_grupos, 'r', encoding='utf-8') as f:
                        datos = json.load(f)
                    for i, g in enumerate(datos['grupos']):
                        if i < len(vars_sel):
                            datos['grupos'][i]['seleccionado'] = vars_sel[i].get()
                        if i < len(vars_msg):
                            val = vars_msg[i].get()
                            datos['grupos'][i]['mensaje_asignado'] = None if val == "🎲 Aleatorio" else val
                    with open(self.archivo_grupos, 'w', encoding='utf-8') as f:
                        json.dump(datos, f, ensure_ascii=False, indent=2)
                    Toast.exito(self.root, "Destinatarios\nGuardados correctamente")
                    ventana.grab_release()
                    ventana.destroy()
                except Exception as e:
                    messagebox.showerror("❌ Error", f"Error guardando: {e}")

            frame_footer = tk.Frame(ventana, bg="#f0f0f0", padx=20)
            frame_footer.pack(fill='x', pady=(8, 15))
            tk.Button(frame_footer, text="Cancelar", font=("Segoe UI", 10),
                      bg="#e0e0e0", command=lambda: [ventana.grab_release(), ventana.destroy()],
                      width=12).pack(side='left')
            tk.Button(frame_footer, text="💾 Guardar", font=("Segoe UI", 10, "bold"),
                      bg="#17a2b8", fg="white", command=guardar_seleccion,
                      width=14).pack(side='right')

        ventana.protocol("WM_DELETE_WINDOW", lambda: [ventana.grab_release(), ventana.destroy()])
        x = (self.root.winfo_screenwidth() // 2) - 220
        y = (self.root.winfo_screenheight() // 2) - 200
        ventana.geometry(f'440x380+{x}+{y}')
        ventana.deiconify()

    def _guardar_grupo_nuevo(self, nombre, tipo):
        datos = {"grupos": []}
        if os.path.exists(self.archivo_grupos):
            try:
                with open(self.archivo_grupos, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
            except:
                pass
        datos['grupos'].append({"nombre": nombre, "tipo": tipo, "activo": True, "descripcion": ""})
        os.makedirs(os.path.dirname(self.archivo_grupos), exist_ok=True)
        with open(self.archivo_grupos, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)

    def ejecutar(self):
        self.root.mainloop()


def main():
    app = ConfiguradorGUI()
    app.ejecutar()


if __name__ == "__main__":
    main()