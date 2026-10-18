# Archivo: selector_destinatarios.py
# Ruta: compartido/selector_destinatarios.py
# Uso: from compartido.selector_destinatarios import SelectorDestinatarios
import os
import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox


class SelectorDestinatarios:
    """Ventana para marcar destinatarios de oración y el mensaje de cada uno"""

    OPCION_ALEATORIO = "🎲 Aleatorio"

    @staticmethod
    def _base_dir():
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    def leer_grupos_activos():
        """Grupos y contactos activos registrados en llamados-oracion/grupos.json"""
        ruta = os.path.join(SelectorDestinatarios._base_dir(), "llamados-oracion", "grupos.json")
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                return [g for g in json.load(f).get('grupos', []) if g.get('activo', True)]
        except Exception:
            return []

    @staticmethod
    def leer_mensajes_oracion():
        """Retorna (mensajes_grupos, mensajes_individuales) desde mensajes_oracion.txt"""
        ruta = os.path.join(SelectorDestinatarios._base_dir(), "llamados-oracion", "mensajes_oracion.txt")
        if not os.path.exists(ruta):
            return [], []

        with open(ruta, 'r', encoding='utf-8') as f:
            contenido = f.read()

        if '[GRUPOS]' in contenido and '[INDIVIDUALES]' in contenido:
            partes = contenido.split('[INDIVIDUALES]')
            mensajes_grupos = [l.strip() for l in partes[0].replace('[GRUPOS]', '').strip().split('\n') if l.strip()]
            mensajes_individuales = [l.strip() for l in partes[1].strip().split('\n') if l.strip()]
            return mensajes_grupos, mensajes_individuales

        todas = [l.strip() for l in contenido.split('\n') if l.strip() and not l.startswith('[')]
        return todas, todas

    @staticmethod
    def nombre_corto(nombre, maximo=17):
        """Acorta nombres largos solo para mostrarlos; el nombre completo se usa al enviar"""
        return nombre if len(nombre) <= maximo else nombre[:maximo].rstrip() + "…"

    @staticmethod
    def seleccionar(parent, preseleccion=None, titulo="📱 Destinatarios de oración",
                    subtitulo="Marca quién recibe la oración", texto_boton="✅ Aceptar", color="#25D366"):
        """
        Abre la ventana de forma modal y espera la respuesta.

        Args:
            parent: ventana padre
            preseleccion: lista de {'nombre', 'mensaje_asignado'} ya elegidos; si es None se
                          usan los destinatarios por defecto ('seleccionado' en grupos.json)

        Returns:
            list[dict] con {'nombre', 'tipo', 'mensaje_asignado'} o None si se canceló
        """
        grupos = SelectorDestinatarios.leer_grupos_activos()
        if not grupos:
            messagebox.showwarning(
                "⚠️ Sin grupos ni contactos",
                "No hay grupos ni contactos registrados para oraciones.\n\n"
                "Agrégalos en Configurador → Oraciones.",
                parent=parent
            )
            return None

        elegidos_previos = None
        if preseleccion is not None:
            elegidos_previos = {d['nombre']: d.get('mensaje_asignado') for d in preseleccion}

        resultado = {'valor': None}

        ventana = tk.Toplevel(parent)
        ventana.withdraw()
        ventana.title(titulo)
        ventana.resizable(False, False)
        ventana.configure(bg="#f0f0f0")
        # Si la ventana padre está oculta, Windows también ocultaría a esta ventana
        if parent.winfo_viewable():
            ventana.transient(parent)
        ventana.grab_set()

        def cerrar():
            ventana.grab_release()
            ventana.destroy()

        header = tk.Frame(ventana, bg=color, pady=12)
        header.pack(fill='x')
        tk.Label(header, text=titulo, font=("Segoe UI", 12, "bold"), bg=color, fg="white").pack()
        tk.Label(header, text=subtitulo, font=("Segoe UI", 8), bg=color, fg="white").pack()

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

        mensajes_grupos, mensajes_individuales = SelectorDestinatarios.leer_mensajes_oracion()

        for g in grupos:
            if elegidos_previos is None:
                marcado = g.get('seleccionado', True)
                guardado = g.get('mensaje_asignado')
            else:
                marcado = g['nombre'] in elegidos_previos
                guardado = elegidos_previos.get(g['nombre'], g.get('mensaje_asignado'))

            var = tk.BooleanVar(value=marcado)
            vars_sel.append(var)

            disponibles = mensajes_grupos if g.get('tipo') == 'grupo' else mensajes_individuales
            var_msg = tk.StringVar(value=guardado if guardado in disponibles else SelectorDestinatarios.OPCION_ALEATORIO)
            vars_msg.append(var_msg)

            fila = tk.Frame(frame_scroll, bg="#f0f0f0")
            fila.pack(fill='x', pady=3)
            icono = "👥" if g.get('tipo') == 'grupo' else "👤"
            tk.Checkbutton(fila, text=f"{icono} {SelectorDestinatarios.nombre_corto(g['nombre'])}", variable=var,
                           bg="#f0f0f0", font=("Segoe UI", 10), width=20, anchor='w').pack(side='left')
            ttk.Combobox(fila, textvariable=var_msg, values=[SelectorDestinatarios.OPCION_ALEATORIO] + disponibles,
                         state='readonly', width=30, font=("Segoe UI", 8)).pack(side='left', padx=(5, 0))

        def actualizar_todos(*_):
            var_todos.set(all(v.get() for v in vars_sel))
        for v in vars_sel:
            v.trace_add('write', actualizar_todos)
        actualizar_todos()

        def aceptar():
            elegidos = []
            for g, var, var_msg in zip(grupos, vars_sel, vars_msg):
                if var.get():
                    elegidos.append({
                        'nombre': g['nombre'],
                        'tipo': g.get('tipo', 'grupo'),
                        'mensaje_asignado': None if var_msg.get() == SelectorDestinatarios.OPCION_ALEATORIO else var_msg.get()
                    })
            if not elegidos:
                messagebox.showwarning("⚠️ Aviso", "Marca al menos un destinatario", parent=ventana)
                return
            resultado['valor'] = elegidos
            cerrar()

        frame_footer = tk.Frame(ventana, bg="#f0f0f0", padx=20)
        frame_footer.pack(fill='x', pady=(8, 15))
        tk.Button(frame_footer, text="Cancelar", font=("Segoe UI", 10),
                  bg="#e0e0e0", command=cerrar, width=12).pack(side='left')
        tk.Button(frame_footer, text=texto_boton, font=("Segoe UI", 10, "bold"),
                  bg=color, fg="white", command=aceptar, width=14).pack(side='right')

        ventana.protocol("WM_DELETE_WINDOW", cerrar)
        ventana.update_idletasks()
        ancho, alto = 500, 410
        x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
        y = (ventana.winfo_screenheight() // 2) - (alto // 2)
        ventana.geometry(f'{ancho}x{alto}+{x}+{y}')
        ventana.deiconify()

        parent.wait_window(ventana)
        return resultado['valor']