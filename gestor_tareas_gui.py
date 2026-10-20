import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
from datetime import datetime
from gestor_licencias import GestorLicencias
from compartido.gestor_archivos import (
    id_tarea,
    obtener_config_tarea,
    guardar_config_tarea,
    eliminar_config_tarea,
    id_de_nombre_tarea,
    migrar_tareas_antiguas,
    modulos_secuencia_general,
    MODULOS_DISPONIBLES
)
from compartido.selector_destinatarios import SelectorDestinatarios


class GestorTareasGUI:
    """Gestor de tareas automáticas - Windows Task Scheduler"""

    def __init__(self):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('AutomaPro.GestorTareasMensajes')
        except Exception:
            pass

        self.root = tk.Tk()
        self.root.withdraw()

        self.root.title("🗓️ Gestor de Tareas Automáticas")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f0f0")

        try:
            base_ico = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            self.root.iconbitmap(os.path.join(base_ico, 'iconos', 'calendar.ico'))
            # default= hace que las subventanas (Toplevel) hereden el ícono en vez de la pluma de Tkinter
            self.root.iconbitmap(default=os.path.join(base_ico, 'iconos', 'calendar.ico'))
        except Exception:
            pass

        x = (self.root.winfo_screenwidth() // 2) - 450
        y = (self.root.winfo_screenheight() // 2) - 300
        # Aplicar icono ANTES de mostrar la ventana
        try:
            base_ico = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            ico = os.path.join(base_ico, 'iconos', 'calendar.ico')
            self.root.iconbitmap(ico)
        except Exception:
            pass

        self.root.geometry(f'900x600+{x}+{y}')
        self.root.deiconify()

        # Reaplicar icono múltiples veces por si Windows lo sobreescribe
        try:
            self.root.after(50, lambda: self.root.iconbitmap(ico))
            self.root.after(200, lambda: self.root.iconbitmap(ico))
            self.root.after(500, lambda: self.root.iconbitmap(ico))
        except Exception:
            pass

        self.gestor_licencias = GestorLicencias()
        if not self._verificar_licencia_full():
            messagebox.showerror(
                "Licencia Requerida",
                "Esta función requiere licencia FULL.\n\nActualiza tu licencia para acceder."
            )
            self.root.destroy()
            return

        self.prefijo_tarea = "AutomaPro_MensajesBiblicos"
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
            self.ruta_exe = os.path.join(self.base_dir, "MensajesBiblicos.exe")
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            self.ruta_exe = None
        self.ruta_script = os.path.join(self.base_dir, "publicar_facebook.py")
        
        self.dias_map = {
            'L': 'MON', 'M': 'TUE', 'X': 'WED', 
            'J': 'THU', 'V': 'FRI', 'S': 'SAT', 'D': 'SUN'
        }
        
        self.dias_map_inverso = {
            'MON': 'L', 'TUE': 'M', 'WED': 'X',
            'THU': 'J', 'FRI': 'V', 'SAT': 'S', 'SUN': 'D'
        }

        self._construir_ui()
        self._cargar_tareas()

    def _mostrar_toast(self, mensaje, duracion=3000, color="#28a745"):
        toast = tk.Toplevel(self.root)
        toast.withdraw()
        toast.overrideredirect(True)
        
        frame = tk.Frame(toast, bg=color, padx=20, pady=15)
        frame.pack()
        
        tk.Label(frame, text=mensaje, font=("Segoe UI", 11), bg=color, fg="white", justify='center').pack()
        
        toast.update_idletasks()
        w = toast.winfo_width()
        h = toast.winfo_height()
        x = (toast.winfo_screenwidth() // 2) - (w // 2)
        y = toast.winfo_screenheight() - h - 50
        toast.geometry(f'+{x}+{y}')
        toast.deiconify()
        toast.after(duracion, toast.destroy)

    def _verificar_licencia_full(self):
        """Verifica si la licencia es FULL — usa cache primero"""
        try:
            cache = self.gestor_licencias._obtener_cache_local()
            if cache and cache.get('valida'):
                tipo = cache.get('tipo', 'TRIAL')
                return tipo in ['FULL', 'MASTER'] or cache.get('es_developer_permanente', False)

            codigo = self.gestor_licencias.obtener_codigo_guardado()
            if not codigo:
                return False
            resultado = self.gestor_licencias.verificar_licencia(codigo, mostrar_mensajes=False)
            return resultado.get('valida') and (resultado.get('tipo') in ['FULL', 'MASTER'] or resultado.get('developer_permanente'))
        except Exception:
            return False

    def _construir_ui(self):
        header = tk.Frame(self.root, bg="#1a73e8", pady=20)
        header.pack(fill='x')
        
        tk.Label(header, text="🗓️ Gestor de Tareas Automáticas", font=("Segoe UI", 16, "bold"), bg="#1a73e8", fg="white").pack()
        tk.Label(header, text="Programa publicaciones automáticas en días y horarios específicos", font=("Segoe UI", 10), bg="#1a73e8", fg="white").pack()

        toolbar = tk.Frame(self.root, bg="#f0f0f0", pady=15)
        toolbar.pack(fill='x', padx=20)
        
        tk.Button(toolbar, text="➕ Nueva Tarea", font=("Segoe UI", 11, "bold"), bg="#1a73e8", fg="white", width=20, command=self._nueva_tarea).pack(side='left', padx=(0, 10))
        tk.Button(toolbar, text="🔄 Actualizar", font=("Segoe UI", 11), bg="#e0e0e0", width=15, command=self._cargar_tareas).pack(side='left')

        frame_lista = tk.Frame(self.root, bg="#f0f0f0")
        frame_lista.pack(fill='both', expand=True, padx=20, pady=(0, 15))
        
        scrollbar = ttk.Scrollbar(frame_lista)
        scrollbar.pack(side='right', fill='y')
        
        columnas = ('nombre', 'dias', 'acciones', 'proxima', 'estado')
        self.tree = ttk.Treeview(frame_lista, columns=columnas, show='headings', yscrollcommand=scrollbar.set, selectmode='browse')
        
        self.tree.heading('nombre', text='Nombre de Tarea')
        self.tree.heading('dias', text='Días')
        self.tree.heading('acciones', text='Acciones')
        self.tree.heading('proxima', text='Próxima Ejecución')
        self.tree.heading('estado', text='Estado')
        
        self.tree.column('nombre', width=250)
        self.tree.column('dias', width=90)
        self.tree.column('acciones', width=200)
        self.tree.column('proxima', width=190)
        self.tree.column('estado', width=110)
        
        self.tree.pack(fill='both', expand=True)
        scrollbar.config(command=self.tree.yview)
        self.tree.bind('<Double-1>', lambda e: self._editar_tarea())

        acciones_frame = tk.Frame(self.root, bg="#f0f0f0")
        acciones_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        tk.Button(acciones_frame, text="📋 Ver Detalles", font=("Segoe UI", 10), bg="#17a2b8", fg="white", width=15, command=self._ver_detalles).pack(side='left', padx=(0, 10))
        tk.Button(acciones_frame, text="✏️ Editar", font=("Segoe UI", 10), bg="#ffc107", width=12, command=self._editar_tarea).pack(side='left', padx=(0, 10))
        tk.Button(acciones_frame, text="🗑️ Eliminar", font=("Segoe UI", 10), bg="#dc3545", fg="white", width=12, command=self._eliminar_tarea).pack(side='left')

    def _cargar_tareas(self, migrar=True):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            resultado = subprocess.run(
                ['schtasks', '/Query', '/FO', 'CSV'],
                capture_output=True,
                text=True,
                encoding='cp850',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if resultado.returncode != 0:
                self.tree.insert('', 'end', values=('Error cargando tareas', '', '', '', ''))
                return
            
            lineas = resultado.stdout.strip().split('\n')
            tareas_encontradas = False
            por_migrar = []
            
            for linea in lineas[1:]:
                partes = linea.split('","')
                if len(partes) >= 3:
                    nombre = partes[0].replace('"', '').strip()
                    proxima = partes[1].replace('"', '').strip() if len(partes) > 1 else 'N/A'
                    estado_raw = partes[2].replace('"', '').strip() if len(partes) > 2 else 'N/A'
                    
                    if self.prefijo_tarea in nombre:
                        nombre_corto = nombre.split('\\')[-1]
                        detalles = self._obtener_detalles_tarea(nombre_corto)
                        dias_texto = self._extraer_dias_cortos(detalles) if detalles else 'N/A'
                        comando = detalles.get('comando', '') if detalles else ''
                        if comando and '--tarea' not in comando:
                            por_migrar.append((nombre_corto, comando))
                        acciones = self._resumen_acciones(self._id_de(nombre_corto))
                        
                        estado_lower = estado_raw.lower()
                        if any(x in estado_lower for x in ['ready', 'listo', 'en espera', 'queued']):
                            estado = '✅ Activa'
                        elif any(x in estado_lower for x in ['disabled', 'deshabilitado', 'desactivado']):
                            estado = '⏸️ Pausada'
                        elif any(x in estado_lower for x in ['running', 'en ejecución', 'ejecutando']):
                            estado = '▶️ En ejecución'
                        else:
                            estado = estado_raw
                        
                        self.tree.insert('', 'end', values=(nombre_corto, dias_texto, acciones, proxima, estado))
                        tareas_encontradas = True
            
            if not tareas_encontradas:
                self.tree.insert('', 'end', values=('No hay tareas programadas', '', '', '', ''))

            if migrar and por_migrar:
                migradas = migrar_tareas_antiguas()
                if migradas:
                    self._cargar_tareas(migrar=False)
                    self._mostrar_toast(f"🔄 {migradas} tarea(s) actualizada(s) al formato nuevo\nMantienen sus días, hora y acciones", duracion=4500)
        
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar tareas:\n{e}")

    def _obtener_detalles_tarea(self, nombre_tarea):
        try:
            nombre_completo = f"{self.prefijo_tarea}_{nombre_tarea}" if not nombre_tarea.startswith(self.prefijo_tarea) else nombre_tarea
            
            resultado = subprocess.run(
                ['schtasks', '/Query', '/TN', nombre_completo, '/FO', 'LIST', '/V'],
                capture_output=True,
                text=True,
                encoding='cp850',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if resultado.returncode != 0:
                return None
            
            detalles = {}
            for linea in resultado.stdout.split('\n'):
                linea = linea.strip()
                if ':' in linea:
                    partes = linea.split(':', 1)
                    clave = partes[0].strip()
                    valor = partes[1].strip() if len(partes) > 1 else ''
                    
                    if 'Tarea que se ejecutar' in clave or 'Task To Run' in clave:
                        detalles['comando'] = valor
                    elif 'Hora de inicio' in clave or 'Start Time' in clave:
                        detalles['horario'] = valor
                    elif 'Tipo de programación' in clave or 'Schedule Type' in clave:
                        detalles['frecuencia'] = valor
                    elif 'Estado' in clave or 'Status' in clave:
                        detalles['estado'] = valor
                    elif 'Días' in clave or 'Days' in clave:
                        detalles['dias_raw'] = valor
                        valor_upper = valor.upper()
                        # Windows en español devuelve "Todos los días de la semana"
                        # Windows en inglés devuelve "Every Day"
                        if 'TODOS' in valor_upper or 'EVERY DAY' in valor_upper or 'CADA' in valor_upper or valor_upper.strip() in ('*', 'ALL'):
                            detalles['dias_raw'] = 'MON,TUE,WED,THU,FRI,SAT,SUN'
                            detalles['dias'] = 'Todos los días'
                        else:
                            dias_eng_esp = {
                                'MON': 'Lun', 'TUE': 'Mar', 'WED': 'Mié',
                                'THU': 'Jue', 'FRI': 'Vie', 'SAT': 'Sáb', 'SUN': 'Dom'
                            }
                            for eng, esp in dias_eng_esp.items():
                                valor_upper = valor_upper.replace(eng, esp)
                            detalles['dias'] = valor_upper
                    elif 'Hora próxima ejecución' in clave or 'Next Run Time' in clave:
                        detalles['Hora próxima ejecución'] = valor
            
            return detalles
        
        except Exception as e:
            print(f"Error obteniendo detalles: {e}")
            return None

    def _extraer_dias_cortos(self, detalles):
        if not detalles:
            return 'N/A'
        
        tipo_prog = detalles.get('frecuencia', '').lower()
        dias = detalles.get('dias', '')
        
        if 'diaria' in tipo_prog or 'daily' in tipo_prog:
            return 'Diario'
        
        if not dias or dias == 'N/A':
            return 'Semanal'
        
        dias_map_eng = {'mon': 'Lun', 'tue': 'Mar', 'wed': 'Mié', 'thu': 'Jue', 'fri': 'Vie', 'sat': 'Sáb', 'sun': 'Dom'}
        dias_lower = dias.lower()
        
        # Windows español: "todos los días de la semana" o "Cada un día(s)" para diaria
        if 'todos' in dias_lower or 'every day' in dias_lower or 'cada' in dias_lower:
            return 'Todos los días'
        
        todos = all(eng in dias_lower for eng in dias_map_eng.keys())
        if todos:
            return 'Todos'
        
        dias_cortos = [esp for eng, esp in dias_map_eng.items() if eng in dias_lower]
        return ', '.join(dias_cortos) if dias_cortos else 'Semanal'

    def _ver_detalles(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona una tarea para ver detalles")
            return
        
        item = self.tree.item(seleccion[0])
        nombre_tarea = item['values'][0]
        
        if nombre_tarea == 'No hay tareas programadas':
            return
        
        if nombre_tarea.startswith('\\'):
            nombre_tarea = nombre_tarea[1:]
        
        detalles = self._obtener_detalles_tarea(nombre_tarea)
        if not detalles:
            messagebox.showerror("Error", "No se pudieron obtener los detalles")
            return
        
        ventana = tk.Toplevel(self.root)
        ventana.withdraw()
        ventana.title(f"Detalles: {nombre_tarea}")
        ventana.resizable(False, False)
        ventana.configure(bg="#f0f0f0")
        ventana.transient(self.root)
        ventana.grab_set()
        
        header = tk.Frame(ventana, bg="#1a73e8", pady=15)
        header.pack(fill='x')
        tk.Label(header, text=f"📋 {nombre_tarea}", font=("Segoe UI", 12, "bold"), bg="#1a73e8", fg="white").pack()
        
        contenido = tk.Frame(ventana, bg="white", relief='solid', borderwidth=1)
        contenido.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Normalizar frecuencia: si todos los días están seleccionados, mostrar siempre igual
        frecuencia_raw = detalles.get('frecuencia', 'N/A')
        dias_val = detalles.get('dias', '')
        if dias_val == 'Todos los días':
            frecuencia_mostrar = 'Diariamente'
        elif 'diaria' in frecuencia_raw.lower() or 'daily' in frecuencia_raw.lower():
            frecuencia_mostrar = 'Diariamente'
        elif 'semanal' in frecuencia_raw.lower() or 'weekly' in frecuencia_raw.lower():
            frecuencia_mostrar = 'Semanal'
        else:
            frecuencia_mostrar = frecuencia_raw

        for etiqueta, valor in [
            ("Horario:", detalles.get('horario', 'N/A')),
            ("Frecuencia:", frecuencia_mostrar),
            ("Días:", detalles.get('dias', 'N/A')),
            ("Estado:", detalles.get('estado', 'N/A')),
            ("Próxima ejecución:", detalles.get('Hora próxima ejecución', 'N/A')),
            ("Acciones:", self._resumen_acciones(self._id_de(nombre_tarea)))
        ]:
            item_frame = tk.Frame(contenido, bg="white")
            item_frame.pack(fill='x', padx=15, pady=5)
            tk.Label(item_frame, text=etiqueta, font=("Segoe UI", 10, "bold"), bg="white", width=20, anchor='w').pack(side='left')
            tk.Label(item_frame, text=valor, font=("Segoe UI", 10), bg="white", anchor='w').pack(side='left')
        
        tk.Button(ventana, text="Cerrar", font=("Segoe UI", 10), bg="#6c757d", fg="white", command=ventana.destroy, width=15).pack(pady=(0, 20))
        
        x = (ventana.winfo_screenwidth() // 2) - 250
        y = (ventana.winfo_screenheight() // 2) - 200
        ventana.geometry(f'500x400+{x}+{y}')
        ventana.deiconify()

    def _editar_tarea(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona una tarea para editar")
            return
        
        item = self.tree.item(seleccion[0])
        nombre_tarea = item['values'][0]
        
        if nombre_tarea == 'No hay tareas programadas':
            return
        
        if nombre_tarea.startswith('\\'):
            nombre_tarea = nombre_tarea[1:]
        
        detalles = self._obtener_detalles_tarea(nombre_tarea)
        if not detalles:
            messagebox.showerror("Error", "No se pudieron obtener los detalles de la tarea")
            return
        
        hora_inicial, minuto_inicial = self._hora_24(detalles.get('horario', '09:00:00'))
        
        tipo_programacion = detalles.get('frecuencia', '').lower()
        dias_actuales = detalles.get('dias', '')
        es_diaria = 'diaria' in tipo_programacion or 'daily' in tipo_programacion

        self._mostrar_formulario_tarea(
            titulo=f"✏️ Editar: {nombre_tarea}",
            color_header="#ffc107",
            nombre_tarea=nombre_tarea,
            hora_inicial=hora_inicial,
            minuto_inicial=minuto_inicial,
            es_diaria=es_diaria,
            dias_iniciales=detalles.get('dias_raw', dias_actuales),
            es_edicion=True
        )

    def _nueva_tarea(self):
        nombre_auto = f"Tarea_{datetime.now().strftime('%Y%m%d_%H%M')}"
        self._mostrar_formulario_tarea(
            titulo="➕ Nueva Tarea Automática",
            color_header="#28a745",
            nombre_tarea=nombre_auto,
            hora_inicial="09",
            minuto_inicial="00",
            es_diaria=True,
            dias_iniciales="",
            es_edicion=False
        )

    def _mostrar_formulario_tarea(self, titulo, color_header, nombre_tarea, hora_inicial, minuto_inicial, es_diaria, dias_iniciales, es_edicion):
        ventana = tk.Toplevel(self.root)
        ventana.withdraw()
        ventana.title(titulo)
        ventana.resizable(False, False)
        ventana.configure(bg="#f0f0f0")
        ventana.transient(self.root)
        ventana.grab_set()
        
        header = tk.Frame(ventana, bg=color_header, pady=15)
        header.pack(fill='x')
        tk.Label(header, text=titulo, font=("Segoe UI", 14, "bold"), bg=color_header, fg="white" if color_header != "#ffc107" else "black").pack()
        
        notebook = ttk.Notebook(ventana)
        notebook.pack(fill='both', expand=True, padx=15, pady=(10, 0))
        tab_horario = tk.Frame(notebook, bg="#f0f0f0")
        tab_acciones = tk.Frame(notebook, bg="#f0f0f0")
        notebook.add(tab_horario, text="📅 Horario")
        notebook.add(tab_acciones, text="⚡ Acciones")

        form = tk.Frame(tab_horario, bg="#f0f0f0")
        form.pack(fill='both', expand=True, padx=10, pady=15)

        obtener_acciones = self._construir_pestana_acciones(tab_acciones, self._id_de(nombre_tarea) if es_edicion else None)
        
        tk.Label(form, text="Nombre de la tarea:", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', pady=(0, 3))
        
        if es_edicion:
            tk.Label(form, text=nombre_tarea, font=("Segoe UI", 10), bg="#f0f0f0", fg="gray").pack(anchor='w', pady=(0, 10))
            entry_nombre = None
        else:
            entry_nombre = tk.Entry(form, font=("Segoe UI", 10), width=50)
            entry_nombre.pack(anchor='w', pady=(0, 10))
            entry_nombre.insert(0, nombre_tarea)
        
        tk.Label(form, text="Frecuencia:", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', pady=(0, 3))
        var_frecuencia = tk.StringVar(value="DAILY" if es_diaria else "WEEKLY")
        
        frame_freq = tk.Frame(form, bg="#f0f0f0")
        frame_freq.pack(anchor='w', pady=(0, 10))
        
        tk.Label(form, text="Días de la semana:", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', pady=(0, 3))
        
        frame_dias = tk.Frame(form, bg="#f0f0f0")
        frame_dias.pack(anchor='w', pady=(0, 10))
        
        dias_vars = {}
        dias_labels = [('L', 'Lunes'), ('M', 'Martes'), ('X', 'Miércoles'), ('J', 'Jueves'), ('V', 'Viernes'), ('S', 'Sábado'), ('D', 'Domingo')]
        
        dias_seleccionados = []
        if dias_iniciales:
            dias_upper = dias_iniciales.upper()
            mapa = {'MON': 'L', 'TUE': 'M', 'WED': 'X', 'THU': 'J', 'FRI': 'V', 'SAT': 'S', 'SUN': 'D'}
            for eng, corto in mapa.items():
                if eng in dias_upper:
                    dias_seleccionados.append(corto)
        
        checkboxes = []
        for corto, completo in dias_labels:
            var = tk.BooleanVar(value=corto in dias_seleccionados)
            dias_vars[corto] = var
            cb = tk.Checkbutton(frame_dias, text=completo, variable=var, bg="#f0f0f0")
            cb.pack(side='left', padx=(0, 10))
            checkboxes.append(cb)
        
        def cambio_frecuencia():
            if var_frecuencia.get() == "DAILY":
                for corto, var in dias_vars.items():
                    var.set(True)
                for cb in checkboxes:
                    cb.config(state='disabled')
            else:
                for cb in checkboxes:
                    cb.config(state='normal')
        
        tk.Radiobutton(frame_freq, text="Diaria", variable=var_frecuencia, value="DAILY", bg="#f0f0f0", command=cambio_frecuencia).pack(side='left', padx=(0, 15))
        tk.Radiobutton(frame_freq, text="Semanal", variable=var_frecuencia, value="WEEKLY", bg="#f0f0f0", command=cambio_frecuencia).pack(side='left')
        
        # Aplicar estado inicial
        if es_diaria:
            for corto, var in dias_vars.items():
                var.set(True)
            for cb in checkboxes:
                cb.config(state='disabled')
        
        tk.Label(form, text="Horario (HH:MM formato 24h):", font=("Segoe UI", 10, "bold"), bg="#f0f0f0").pack(anchor='w', pady=(5, 3))
        
        frame_hora = tk.Frame(form, bg="#f0f0f0")
        frame_hora.pack(anchor='w', pady=(0, 5))
        
        vcmd_hora = (ventana.register(lambda text: len(text) <= 2 and (text.isdigit() or text == "")), '%P')
        
        entry_hora = tk.Entry(frame_hora, font=("Segoe UI", 10), width=5, validate='key', validatecommand=vcmd_hora)
        entry_hora.pack(side='left')
        entry_hora.insert(0, hora_inicial)
        
        tk.Label(frame_hora, text=":", font=("Segoe UI", 10), bg="#f0f0f0").pack(side='left', padx=5)
        
        entry_minuto = tk.Entry(frame_hora, font=("Segoe UI", 10), width=5, validate='key', validatecommand=vcmd_hora)
        entry_minuto.pack(side='left')
        entry_minuto.insert(0, minuto_inicial)
        
        def auto_salto_hora(event):
            if len(entry_hora.get()) == 2:
                entry_minuto.focus()
                entry_minuto.select_range(0, tk.END)
        
        entry_hora.bind('<KeyRelease>', auto_salto_hora)
        
        frame_btns = tk.Frame(ventana, bg="#f0f0f0")
        frame_btns.pack(fill='x', side='bottom', pady=(5, 15))
        
        tk.Button(frame_btns, text="Cancelar", font=("Segoe UI", 10), bg="#6c757d", fg="white", width=12, command=ventana.destroy).pack(side='left', padx=(30, 10))
        
        def guardar():
            nombre = nombre_tarea if es_edicion else entry_nombre.get().strip()
            if not nombre:
                messagebox.showerror("Error", "Debes ingresar un nombre")
                return

            acciones = obtener_acciones()
            if acciones is None:
                notebook.select(tab_acciones)
                return
            
            frecuencia = var_frecuencia.get()
            dias_selec = []
            if frecuencia == "WEEKLY":
                for corto, var in dias_vars.items():
                    if var.get():
                        dias_selec.append(self.dias_map[corto])
                if not dias_selec:
                    messagebox.showerror("Error", "Debes seleccionar al menos un día para tarea semanal")
                    return
            
            hora = entry_hora.get().strip()
            minuto = entry_minuto.get().strip()
            
            if not hora or not minuto or not hora.isdigit() or not minuto.isdigit():
                messagebox.showerror("Error", "Hora y minuto deben ser números")
                return
            
            hora_int = int(hora)
            minuto_int = int(minuto)
            
            if hora_int < 0 or hora_int > 23:
                messagebox.showerror("Error", "La hora debe estar entre 00 y 23")
                return
            if minuto_int < 0 or minuto_int > 59:
                messagebox.showerror("Error", "Los minutos deben estar entre 00 y 59")
                return
            
            horario = f"{hora_int:02d}:{minuto_int:02d}"
            
            ahora = datetime.now()
            hora_tarea = datetime.now().replace(hour=hora_int, minute=minuto_int, second=0, microsecond=0)
            mostrar_aviso_hora = False
            
            if frecuencia == "DAILY" and hora_tarea <= ahora:
                mostrar_aviso_hora = True
                mensaje_aviso = f"⏰ Se programará para mañana a las {horario}"
            elif frecuencia == "WEEKLY":
                dias_semana_eng = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
                dia_actual = dias_semana_eng[ahora.weekday()]
                if dia_actual in dias_selec and hora_tarea <= ahora:
                    dias_nombres = {'MON': 'Lunes', 'TUE': 'Martes', 'WED': 'Miércoles', 'THU': 'Jueves', 'FRI': 'Viernes', 'SAT': 'Sábado', 'SUN': 'Domingo'}
                    mostrar_aviso_hora = True
                    mensaje_aviso = f"⏰ Se ejecutará el próximo {dias_nombres.get(dia_actual, 'día')} a las {horario}"
            
            if es_edicion:
                n = nombre[1:] if nombre.startswith('\\') else nombre
                nombre_completo = n if n.startswith(self.prefijo_tarea) else f"{self.prefijo_tarea}_{n}"
                subprocess.run(['schtasks', '/Delete', '/TN', nombre_completo, '/F'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            guardar_config_tarea(self._id_de(nombre), nombre, acciones['modulos'], acciones['destinatarios'])
            ventana.destroy()
            self._crear_tarea_windows(nombre, frecuencia, horario, dias_selec if frecuencia == "WEEKLY" else None, mostrar_aviso_hora)
            
            if mostrar_aviso_hora:
                self.root.after(100, lambda: self._mostrar_toast(mensaje_aviso, duracion=4000, color="#ffc107"))
        
        texto_boton = "💾 Guardar Cambios" if es_edicion else "✅ Crear Tarea"
        tk.Button(frame_btns, text=texto_boton, font=("Segoe UI", 10, "bold"), bg="#28a745", fg="white", width=18, command=guardar).pack(side='right', padx=(10, 30))
        
        x = (ventana.winfo_screenwidth() // 2) - 300
        y = (ventana.winfo_screenheight() // 2) - 300
        ventana.geometry(f'600x600+{x}+{y}')
        ventana.deiconify()

    def _crear_tarea_windows(self, nombre, frecuencia, horario, dias=None, ya_mostro_aviso=False):
        try:
            nombre_completo = nombre if nombre.startswith(self.prefijo_tarea) else f"{self.prefijo_tarea}_{nombre}"
            comando_tarea = self._comando_tarea(self._id_de(nombre_completo))
            
            comando = ['schtasks', '/Create', '/TN', nombre_completo, '/TR', comando_tarea, '/SC', frecuencia, '/ST', horario]
            if frecuencia == 'WEEKLY' and dias:
                comando.extend(['/D', ','.join(dias)])
            comando.append('/F')
            
            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if resultado.returncode == 0:
                self._cargar_tareas()
                if not ya_mostro_aviso:
                    detalles = self._obtener_detalles_tarea(nombre_completo)
                    proxima = detalles.get('Hora próxima ejecución', 'próximamente') if detalles else 'próximamente'
                    self._mostrar_toast(f"✅ Tarea programada para {proxima}")
            else:
                messagebox.showerror("❌ Error", f"No se pudo crear la tarea:\n{resultado.stderr}")
        
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error creando tarea:\n{e}")

    def _eliminar_tarea(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Aviso", "Selecciona una tarea para eliminar")
            return
        
        item = self.tree.item(seleccion[0])
        nombre_tarea = item['values'][0]
        
        if nombre_tarea == 'No hay tareas programadas':
            return
        
        if nombre_tarea.startswith('\\'):
            nombre_tarea = nombre_tarea[1:]
        
        if not messagebox.askyesno("Confirmar", f"¿Eliminar la tarea '{nombre_tarea}'?"):
            return
        
        try:
            nombre_completo = nombre_tarea if nombre_tarea.startswith(self.prefijo_tarea) else f"{self.prefijo_tarea}_{nombre_tarea}"
            
            resultado = subprocess.run(
                ['schtasks', '/Delete', '/TN', nombre_completo, '/F'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if resultado.returncode == 0:
                eliminar_config_tarea(self._id_de(nombre_completo))
                self._cargar_tareas()
                self._mostrar_toast("✅ Tarea eliminada correctamente")
            else:
                messagebox.showerror("❌ Error", "No se pudo eliminar la tarea")
        
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error eliminando tarea:\n{e}")

    def _hora_24(self, texto):
        """Convierte la hora que muestra Windows ('01:00:00 p. m.', '1:00:00 PM' o '13:00:00') a ('13', '00')"""
        import re
        coincidencia = re.search(r'(\d{1,2}):(\d{2})', texto or '')
        if not coincidencia:
            return '09', '00'
        hora, minuto = int(coincidencia.group(1)), coincidencia.group(2)
        marca = re.sub(r'[\s.]', '', (texto or '').lower())
        if 'pm' in marca and hora < 12:
            hora += 12
        elif 'am' in marca and hora == 12:
            hora = 0
        return f"{hora:02d}", minuto

    def _construir_pestana_acciones(self, tab, id_de_tarea=None):
        """Arma la pestaña Acciones del formulario y retorna una función que entrega lo elegido (o None si no es válido)"""
        config_tarea = obtener_config_tarea(id_de_tarea) if id_de_tarea else None
        if config_tarea:
            activos = list(config_tarea.get('modulos', []))
            destinatarios = config_tarea.get('destinatarios')
        else:
            activos = modulos_secuencia_general()
            destinatarios = None

        nombres = dict(MODULOS_DISPONIBLES)
        estado = {
            'orden': [m for m in activos if m in nombres] + [m for m in nombres if m not in activos],
            'destinatarios': destinatarios
        }
        vars_activos = {m: tk.BooleanVar(value=m in activos) for m in nombres}

        tk.Label(tab, text="Acciones que ejecuta esta tarea, en orden", font=("Segoe UI", 10, "bold"),
                 bg="#f0f0f0").pack(anchor='w', padx=15, pady=(12, 4))
        contenedor = tk.Frame(tab, bg="#f0f0f0")
        contenedor.pack(fill='x', padx=15)

        def mover(modulo, direccion):
            i = estado['orden'].index(modulo)
            j = i + direccion
            if 0 <= j < len(estado['orden']):
                estado['orden'][i], estado['orden'][j] = estado['orden'][j], estado['orden'][i]
                dibujar()

        def dibujar():
            for w in contenedor.winfo_children():
                w.destroy()
            for modulo in estado['orden']:
                fila = tk.Frame(contenedor, bg="white", relief='solid', borderwidth=1)
                fila.pack(fill='x', pady=2)
                tk.Checkbutton(fila, text=nombres[modulo], variable=vars_activos[modulo], font=("Segoe UI", 10),
                               bg="white", anchor='w').pack(side='left', padx=8, pady=2, fill='x', expand=True)
                tk.Button(fila, text="↓", width=3, command=lambda m=modulo: mover(m, 1)).pack(side='right', padx=(0, 6))
                tk.Button(fila, text="↑", width=3, command=lambda m=modulo: mover(m, -1)).pack(side='right')

        dibujar()

        tk.Label(tab, text="💡 'Publicar Prédica' siempre se ejecuta después de 'Extraer'",
                 font=("Segoe UI", 8), fg="#1a73e8", bg="#f0f0f0").pack(anchor='w', padx=15, pady=(4, 10))
        tk.Frame(tab, bg="#ccc", height=1).pack(fill='x', padx=15)

        tk.Label(tab, text="📱 Destinatarios de oraciones", font=("Segoe UI", 10, "bold"),
                 bg="#f0f0f0").pack(anchor='w', padx=15, pady=(10, 4))
        var_modo = tk.StringVar(value='propios' if destinatarios else 'defecto')
        tk.Radiobutton(tab, text="Usar los destinatarios por defecto", variable=var_modo, value='defecto',
                       bg="#f0f0f0", font=("Segoe UI", 10)).pack(anchor='w', padx=25)

        fila_propios = tk.Frame(tab, bg="#f0f0f0")
        fila_propios.pack(anchor='w', padx=25, fill='x')
        tk.Radiobutton(fila_propios, text="Elegir para esta tarea", variable=var_modo, value='propios',
                       bg="#f0f0f0", font=("Segoe UI", 10)).pack(side='left')
        lbl_elegidos = tk.Label(fila_propios, font=("Segoe UI", 9), fg="#555", bg="#f0f0f0")

        def actualizar_elegidos():
            cantidad = len(estado['destinatarios'] or [])
            lbl_elegidos.config(text=f"{cantidad} elegido(s)" if cantidad else "ninguno elegido")

        def elegir():
            formulario = tab.winfo_toplevel()
            elegidos = SelectorDestinatarios.seleccionar(
                formulario,
                preseleccion=estado['destinatarios'],
                titulo="📱 Destinatarios de esta tarea",
                subtitulo="Solo esta tarea enviará la oración a los que marques"
            )
            # El selector libera el bloqueo de la ventana al cerrarse; el formulario lo recupera
            formulario.grab_set()
            if elegidos is not None:
                estado['destinatarios'] = elegidos
                var_modo.set('propios')
                actualizar_elegidos()

        tk.Button(fila_propios, text="✅ Elegir…", font=("Segoe UI", 9), bg="#25D366", fg="white",
                  command=elegir).pack(side='left', padx=(10, 6))
        lbl_elegidos.pack(side='left')
        actualizar_elegidos()

        def obtener():
            modulos = [m for m in estado['orden'] if vars_activos[m].get()]
            if not modulos:
                messagebox.showerror("Error", "Marca al menos una acción en la pestaña ⚡ Acciones", parent=tab)
                return None
            if 'publicar_predica' in modulos and 'extraer' in modulos:
                i, j = modulos.index('publicar_predica'), modulos.index('extraer')
                if i < j:
                    modulos[i], modulos[j] = modulos[j], modulos[i]
            usa_propios = var_modo.get() == 'propios'
            if usa_propios and not estado['destinatarios']:
                messagebox.showerror("Error", "Elegiste destinatarios propios pero no hay ninguno marcado.\n\n"
                                     "Presiona '✅ Elegir…' o usa los destinatarios por defecto.", parent=tab)
                return None
            return {'modulos': modulos, 'destinatarios': estado['destinatarios'] if usa_propios else None}

        return obtener

    def _id_de(self, nombre):
        return id_de_nombre_tarea(nombre)

    def _comando_tarea(self, id_de_tarea):
        """Comando que ejecuta Windows: siempre con --tarea para que nunca se comporte como doble clic"""
        if self.ruta_exe and os.path.exists(self.ruta_exe):
            return f'"{self.ruta_exe}" --tarea={id_de_tarea}'
        directorio_trabajo = os.path.dirname(self.ruta_script)
        return f'cmd /c "cd /d "{directorio_trabajo}" && py "{self.ruta_script}" --tarea={id_de_tarea}"'

    def _resumen_acciones(self, id_de_tarea):
        config_tarea = obtener_config_tarea(id_de_tarea)
        if not config_tarea:
            return "Secuencia general"
        cortos = {'biblico': 'Bíblico', 'extraer': 'Extraer', 'publicar_predica': 'Prédica', 'oraciones': 'Oraciones'}
        partes = []
        for modulo in config_tarea.get('modulos', []):
            texto = cortos.get(modulo, modulo)
            if modulo == 'oraciones' and config_tarea.get('destinatarios'):
                texto += f" ({len(config_tarea['destinatarios'])})"
            partes.append(texto)
        return ", ".join(partes) if partes else "Sin acciones"

    def ejecutar(self):
        self.root.mainloop()


def main():
    gestor = GestorTareasGUI()
    gestor.ejecutar()


if __name__ == "__main__":
    main()