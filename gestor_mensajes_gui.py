import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from compartido.gestor_archivos import leer_mensajes_elegidos, guardar_mensajes_elegidos, quitar_mensaje_elegido


class GestorMensajesGUI:
    """Interfaz gráfica para gestionar mensajes bíblicos (.txt)"""

    def __init__(self):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('AutomaPro.GestorMensajes')
        except Exception:
            pass

        # Ruta siempre relativa al ejecutable, no al directorio de trabajo
        if getattr(sys, 'frozen', False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.abspath(__file__))
        self.carpeta_mensajes = os.path.join(base, "mensajes")

        self.root = tk.Tk()
        self.root.withdraw()

        self.root.title("📝 Gestor de Mensajes Bíblicos")
        self.root.minsize(700, 600)
        self.root.resizable(True, True)
        self.root.configure(bg="#f0f0f0")

        try:
            base_ico = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            self.root.iconbitmap(os.path.join(base_ico, 'iconos', 'edit.ico'))
        except Exception:
            pass

        width = 800
        height = 600
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        self.root.deiconify()

        # Reaplicar icono múltiples veces para garantizar que Windows lo aplique
        try:
            base_ico = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            ico = os.path.join(base_ico, 'iconos', 'edit.ico')
            self.root.after(100, lambda: self.root.iconbitmap(ico))
            self.root.after(300, lambda: self.root.iconbitmap(ico))
            self.root.after(500, lambda: self.root.iconbitmap(ico))
        except Exception:
            pass

        self.es_full = self._verificar_licencia_full()
        self._construir_ui()
        self._cargar_mensajes()

    def _construir_ui(self):

        # Header
        header = tk.Frame(self.root, bg="#1a73e8", pady=12)
        header.pack(fill='x')
        tk.Label(
            header,
            text="📝 Gestor de Mensajes Bíblicos",
            font=("Segoe UI", 14, "bold"),
            bg="#1a73e8",
            fg="white"
        ).pack()

        # Panel principal dividido en 2
        panel = tk.Frame(self.root, bg="#f0f0f0")
        panel.pack(fill='both', expand=True, padx=10, pady=10)

        # ==================== PANEL IZQUIERDO (lista) ====================
        panel_izq = tk.Frame(panel, bg="#f0f0f0", width=250)
        panel_izq.pack(side='left', fill='y', padx=(0, 5))
        panel_izq.pack_propagate(False)

        tk.Label(
            panel_izq,
            text="📂 Mensajes disponibles",
            font=("Segoe UI", 10, "bold"),
            bg="#f0f0f0"
        ).pack(anchor='w', pady=(0, 5))

        self.lbl_contador = tk.Label(
            panel_izq,
            text="0 mensajes",
            font=("Segoe UI", 8),
            fg="gray",
            bg="#f0f0f0"
        )
        self.lbl_contador.pack(anchor='w', pady=(0, 5))

        frame_lista = tk.Frame(panel_izq, bg="#f0f0f0")
        frame_lista.pack(fill='both', expand=True)

        scrollbar = tk.Scrollbar(frame_lista)
        scrollbar.pack(side='right', fill='y')

        self.lista = tk.Listbox(
            frame_lista,
            yscrollcommand=scrollbar.set,
            font=("Segoe UI", 9),
            selectmode='single',
            bg="white",
            relief='solid',
            borderwidth=1
        )
        self.lista.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.lista.yview)

        self.lista.bind('<<ListboxSelect>>', self._on_seleccionar)

        # Botones lista — altura fija para que no se achiquen
        frame_btn_lista = tk.Frame(panel_izq, bg="#f0f0f0")
        frame_btn_lista.pack(fill='x', pady=(8, 0))

        tk.Button(
            frame_btn_lista,
            text="✚ Nuevo",
            font=("Segoe UI", 10, "bold"),
            bg="#1a73e8",
            fg="white",
            command=self._nuevo_mensaje
        ).pack(side='left', expand=True, fill='x', padx=(0, 2), ipady=6)

        tk.Button(
            frame_btn_lista,
            text="🗑️ Eliminar",
            font=("Segoe UI", 10),
            bg="#dc3545",
            fg="white",
            command=self._eliminar_mensaje
        ).pack(side='left', expand=True, fill='x', padx=(2, 0), ipady=6)

        # ==================== COLA DE ELEGIDOS ====================
        if self.es_full:
            tk.Button(
                panel_izq,
                text="📌 Elegir para publicar",
                font=("Segoe UI", 10, "bold"),
                bg="#ffc107",
                fg="#333",
                command=self._elegir_mensaje
            ).pack(fill='x', pady=(6, 0), ipady=4)

            tk.Label(
                panel_izq,
                text="📌 Cola de publicación",
                font=("Segoe UI", 10, "bold"),
                bg="#f0f0f0"
            ).pack(anchor='w', pady=(10, 2))

            self.lista_cola = tk.Listbox(
                panel_izq,
                height=5,
                font=("Segoe UI", 9),
                selectmode='single',
                exportselection=False,
                bg="#fffbe6",
                relief='solid',
                borderwidth=1
            )
            self.lista_cola.pack(fill='x')

            frame_btn_cola = tk.Frame(panel_izq, bg="#f0f0f0")
            frame_btn_cola.pack(fill='x', pady=(4, 0))
            for texto, comando in [
                ("↑", lambda: self._mover_elegido(-1)),
                ("↓", lambda: self._mover_elegido(1)),
                ("✖ Quitar", self._quitar_elegido),
            ]:
                tk.Button(frame_btn_cola, text=texto, font=("Segoe UI", 9), bg="#e0e0e0",
                          command=comando).pack(side='left', expand=True, fill='x', padx=1)

            tk.Label(
                panel_izq,
                text="Se usa en modo Solo elegidos o Híbrido\n(Configurador → Mensajes)",
                font=("Segoe UI", 8),
                fg="#777",
                bg="#f0f0f0",
                justify='left'
            ).pack(anchor='w', pady=(4, 0))
        else:
            tk.Button(
                panel_izq,
                text="🔒 Elegir para publicar — Completa",
                font=("Segoe UI", 9),
                bg="#e0e0e0",
                fg="#9e9e9e",
                command=lambda: messagebox.showinfo(
                    "🔒 Versión Completa",
                    "Elegir mensajes específicos para publicar requiere la versión Completa.\n\n"
                    "Adquiérela en automapro.com")
            ).pack(fill='x', pady=(6, 0), ipady=4)

        # ==================== PANEL DERECHO (editor) ====================
        panel_der = tk.Frame(panel, bg="#f0f0f0")
        panel_der.pack(side='left', fill='both', expand=True)

        tk.Label(
            panel_der,
            text="✏️ Editor de mensaje",
            font=("Segoe UI", 10, "bold"),
            bg="#f0f0f0"
        ).pack(anchor='w', pady=(0, 5))

        frame_nombre = tk.Frame(panel_der, bg="#f0f0f0")
        frame_nombre.pack(fill='x', pady=(0, 8))

        tk.Label(
            frame_nombre,
            text="Archivo:",
            font=("Segoe UI", 9),
            bg="#f0f0f0"
        ).pack(side='left')

        self.lbl_archivo = tk.Label(
            frame_nombre,
            text="(ninguno seleccionado)",
            font=("Segoe UI", 9, "italic"),
            fg="gray",
            bg="#f0f0f0"
        )
        self.lbl_archivo.pack(side='left', padx=5)

        # Panel derecho — botones primero con side='bottom' para que no desaparezcan
        frame_btn_editor = tk.Frame(panel_der, bg="#f0f0f0")
        frame_btn_editor.pack(side='bottom', fill='x', pady=(8, 0))

        tk.Button(
            frame_btn_editor,
            text="🗑️ Limpiar",
            font=("Segoe UI", 10),
            bg="#e0e0e0",
            width=12,
            command=self._limpiar_editor
        ).pack(side='left', padx=(0, 5), ipady=6, pady=0)

        tk.Button(
            frame_btn_editor,
            text="💾 Guardar mensaje",
            font=("Segoe UI", 10, "bold"),
            bg="#1a73e8",
            fg="white",
            width=16,
            command=self._guardar_mensaje
        ).pack(side='right', ipady=6, pady=0)

        frame_texto = tk.Frame(panel_der, bg="#f0f0f0")
        frame_texto.pack(fill='both', expand=True)

        scrollbar_texto = tk.Scrollbar(frame_texto)
        scrollbar_texto.pack(side='right', fill='y')

        self.lbl_chars = tk.Label(
            frame_texto,
            text="0 caracteres",
            font=("Segoe UI", 8),
            fg="gray",
            bg="#f0f0f0"
        )
        self.lbl_chars.pack(side='bottom', anchor='e', pady=(1, 0))

        self.texto = tk.Text(
            frame_texto,
            yscrollcommand=scrollbar_texto.set,
            font=("Segoe UI", 10),
            wrap='word',
            relief='solid',
            borderwidth=1,
            bg="white",
            padx=8,
            pady=8
        )
        self.texto.pack(fill='both', expand=True)
        scrollbar_texto.config(command=self.texto.yview)

        self.texto.bind('<KeyRelease>', self._actualizar_contador_chars)

    def _cargar_mensajes(self):
        """Carga la lista de mensajes desde la carpeta"""
        self.lista.delete(0, tk.END)

        if not os.path.exists(self.carpeta_mensajes):
            os.makedirs(self.carpeta_mensajes)

        mensajes = sorted([
            f for f in os.listdir(self.carpeta_mensajes)
            if f.endswith('.txt')
        ])

        for mensaje in mensajes:
            self.lista.insert(tk.END, mensaje)

        self.lbl_contador.config(text=f"{len(mensajes)} mensajes")
        self._cargar_cola()

    def _on_seleccionar(self, event):
        """Al seleccionar un mensaje de la lista lo muestra en el editor"""
        seleccion = self.lista.curselection()
        if not seleccion:
            return

        nombre = self.lista.get(seleccion[0])
        ruta = os.path.join(self.carpeta_mensajes, nombre)

        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()

            self.texto.delete('1.0', tk.END)
            self.texto.insert('1.0', contenido)
            self.lbl_archivo.config(text=nombre, fg="#1a73e8")
            self._actualizar_contador_chars()

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al leer el mensaje: {e}")

    def _guardar_mensaje(self):
        """Guarda el contenido del editor en el archivo seleccionado"""
        nombre = self.lbl_archivo.cget('text')

        if nombre == "(ninguno seleccionado)":
            messagebox.showwarning("⚠️ Aviso", "Selecciona un mensaje o crea uno nuevo")
            return

        contenido = self.texto.get('1.0', tk.END).strip()

        if not contenido:
            messagebox.showwarning("⚠️ Aviso", "El mensaje no puede estar vacío")
            return

        ruta = os.path.join(self.carpeta_mensajes, nombre)

        try:
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(contenido)
            messagebox.showinfo("✅ Éxito", f"Mensaje guardado: {nombre}")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al guardar: {e}")

    def _nuevo_mensaje(self):
        """Crea un nuevo archivo de mensaje"""
        mensajes_existentes = [
            f for f in os.listdir(self.carpeta_mensajes)
            if f.endswith('.txt')
        ] if os.path.exists(self.carpeta_mensajes) else []

        siguiente_num = len(mensajes_existentes) + 1
        nombre_sugerido = f"mensaje-{siguiente_num:03d}.txt"

        nombre = simpledialog.askstring(
            "Nuevo mensaje",
            "Nombre del archivo:",
            initialvalue=nombre_sugerido,
            parent=self.root
        )

        if not nombre:
            return

        if not nombre.endswith('.txt'):
            nombre += '.txt'

        ruta = os.path.join(self.carpeta_mensajes, nombre)

        if os.path.exists(ruta):
            messagebox.showwarning("⚠️ Aviso", f"Ya existe un archivo llamado {nombre}")
            return

        try:
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write("")

            self._cargar_mensajes()

            for i in range(self.lista.size()):
                if self.lista.get(i) == nombre:
                    self.lista.selection_clear(0, tk.END)
                    self.lista.selection_set(i)
                    self.lista.see(i)
                    self._on_seleccionar(None)
                    break

            self.texto.focus_set()

        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al crear el archivo: {e}")

    def _eliminar_mensaje(self):
        """Elimina el mensaje seleccionado"""
        seleccion = self.lista.curselection()
        if not seleccion:
            messagebox.showwarning("⚠️ Aviso", "Selecciona un mensaje para eliminar")
            return

        nombre = self.lista.get(seleccion[0])

        confirmar = messagebox.askyesno(
            "🗑️ Confirmar eliminación",
            f"¿Estás seguro de eliminar '{nombre}'?\n\nEsta acción no se puede deshacer."
        )

        if not confirmar:
            return

        ruta = os.path.join(self.carpeta_mensajes, nombre)

        try:
            os.remove(ruta)
            quitar_mensaje_elegido(nombre)
            self._cargar_mensajes()
            self._limpiar_editor()
            messagebox.showinfo("✅ Éxito", f"Mensaje eliminado: {nombre}")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error al eliminar: {e}")

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

    def _elegidos_actuales(self):
        existentes = set(self.lista.get(0, tk.END))
        return [m for m in leer_mensajes_elegidos() if m in existentes]

    def _cargar_cola(self):
        """Muestra la cola de elegidos y resalta esos mensajes en la lista principal"""
        if not hasattr(self, 'lista_cola'):
            return

        elegidos = self._elegidos_actuales()
        self.lista_cola.delete(0, tk.END)
        for i, nombre in enumerate(elegidos, 1):
            self.lista_cola.insert(tk.END, f"{i}. {nombre}")

        for i in range(self.lista.size()):
            self.lista.itemconfig(i, bg="#fff3cd" if self.lista.get(i) in elegidos else "white")

    def _elegir_mensaje(self):
        seleccion = self.lista.curselection()
        if not seleccion:
            messagebox.showwarning("⚠️ Aviso", "Selecciona un mensaje de la lista para elegirlo")
            return

        nombre = self.lista.get(seleccion[0])
        elegidos = self._elegidos_actuales()
        if nombre in elegidos:
            messagebox.showinfo("📌 Ya elegido", f"'{nombre}' ya está en la cola (posición {elegidos.index(nombre) + 1})")
            return

        elegidos.append(nombre)
        guardar_mensajes_elegidos(elegidos)
        self._cargar_cola()

    def _mover_elegido(self, direccion):
        seleccion = self.lista_cola.curselection()
        if not seleccion:
            messagebox.showwarning("⚠️ Aviso", "Selecciona un mensaje de la cola para moverlo")
            return

        idx = seleccion[0]
        nuevo = idx + direccion
        elegidos = self._elegidos_actuales()
        if nuevo < 0 or nuevo >= len(elegidos):
            return

        elegidos[idx], elegidos[nuevo] = elegidos[nuevo], elegidos[idx]
        guardar_mensajes_elegidos(elegidos)
        self._cargar_cola()
        self.lista_cola.selection_set(nuevo)

    def _quitar_elegido(self):
        seleccion = self.lista_cola.curselection()
        if not seleccion:
            messagebox.showwarning("⚠️ Aviso", "Selecciona un mensaje de la cola para quitarlo")
            return

        elegidos = self._elegidos_actuales()
        del elegidos[seleccion[0]]
        guardar_mensajes_elegidos(elegidos)
        self._cargar_cola()

    def _limpiar_editor(self):
        """Limpia solo el texto del editor, sin deseleccionar de la lista"""
        self.texto.delete('1.0', tk.END)
        self._actualizar_contador_chars()
        self.texto.focus_set()

    def _actualizar_contador_chars(self, event=None):
        """Actualiza el contador de caracteres"""
        contenido = self.texto.get('1.0', tk.END).strip()
        self.lbl_chars.config(text=f"{len(contenido)} caracteres")

    def ejecutar(self):
        self.root.mainloop()


def main():
    app = GestorMensajesGUI()
    app.ejecutar()


if __name__ == "__main__":
    main()