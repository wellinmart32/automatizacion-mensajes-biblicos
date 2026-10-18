# Archivo: aviso_temporizado.py
# Ruta: compartido/aviso_temporizado.py
# Uso: from compartido.aviso_temporizado import AvisoTemporizado
import tkinter as tk


class AvisoTemporizado:
    """Aviso con cuenta regresiva: se muestra encima de todo y, si nadie responde, aplica la opción por defecto"""

    COLOR_INFO        = "#1a73e8"
    COLOR_ADVERTENCIA = "#e65100"
    COLOR_ERROR       = "#dc3545"

    SEGUNDOS_DEFECTO = 30

    @staticmethod
    def preguntar(titulo, mensaje, opciones, opcion_defecto, segundos=SEGUNDOS_DEFECTO,
                  color=COLOR_ADVERTENCIA, root=None):
        """
        Muestra el aviso y espera la respuesta del usuario o el fin de la cuenta regresiva.

        Args:
            titulo: texto principal del aviso
            mensaje: detalle debajo del título
            opciones: lista de (clave, texto) en el orden en que se muestran los botones
            opcion_defecto: clave que se aplica si nadie responde a tiempo
            segundos: duración de la cuenta regresiva
            color: color del borde, título y botón por defecto
            root: ventana padre opcional; si no hay, se crea una propia (uso desde consola)

        Returns:
            tuple: (clave_elegida, respondio_usuario)
        """
        resultado = {'clave': opcion_defecto, 'respondio': False}
        root_propio = root is None

        try:
            if root_propio:
                root = tk.Tk()
                root.withdraw()

            ventana = tk.Toplevel(root)
            ventana.withdraw()
            # Sin barra de título: no aparece en la barra de tareas ni le quita el teclado a otra ventana
            ventana.overrideredirect(True)
            ventana.attributes('-topmost', True)
            ventana.configure(bg=color)

            ancho = 460

            marco = tk.Frame(ventana, bg="white", padx=20, pady=16)
            marco.pack(fill='both', expand=True, padx=3, pady=3)

            tk.Label(marco, text=titulo, font=("Segoe UI", 12, "bold"), bg="white", fg=color,
                     wraplength=ancho - 50, justify='left').pack(anchor='w')
            tk.Label(marco, text=mensaje, font=("Segoe UI", 10), bg="white", fg="#333",
                     wraplength=ancho - 50, justify='left').pack(anchor='w', pady=(6, 12))

            texto_defecto = dict(opciones).get(opcion_defecto, opcion_defecto)
            lbl_cuenta = tk.Label(marco, font=("Segoe UI", 9), bg="white", fg="#777",
                                  wraplength=ancho - 50, justify='left')
            lbl_cuenta.pack(anchor='w', pady=(0, 10))

            frame_btns = tk.Frame(marco, bg="white")
            frame_btns.pack(fill='x')

            estado = {'restantes': segundos, 'id_after': None}

            def cerrar():
                if estado['id_after']:
                    root.after_cancel(estado['id_after'])
                    estado['id_after'] = None
                ventana.destroy()

            def elegir(clave):
                resultado['clave'] = clave
                resultado['respondio'] = True
                cerrar()

            for clave, texto in reversed(opciones):
                es_defecto = clave == opcion_defecto
                tk.Button(
                    frame_btns,
                    text=texto,
                    font=("Segoe UI", 10, "bold") if es_defecto else ("Segoe UI", 10),
                    bg=color if es_defecto else "#e0e0e0",
                    fg="white" if es_defecto else "#333",
                    cursor="hand2",
                    command=lambda c=clave: elegir(c)
                ).pack(side='right', padx=(8, 0), ipadx=8, ipady=3)

            def actualizar_cuenta():
                lbl_cuenta.config(text=f"⏳ Se aplicará «{texto_defecto}» automáticamente en {estado['restantes']} s")

            def tick():
                estado['restantes'] -= 1
                if estado['restantes'] <= 0:
                    estado['id_after'] = None
                    ventana.destroy()
                    return
                # Reafirmar que siga encima por si otra ventana "siempre visible" lo tapó
                ventana.attributes('-topmost', True)
                actualizar_cuenta()
                estado['id_after'] = root.after(1000, tick)

            actualizar_cuenta()

            ventana.update_idletasks()
            alto = ventana.winfo_reqheight()
            x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
            y = (ventana.winfo_screenheight() // 2) - (alto // 2)
            ventana.geometry(f'{ancho}x{alto}+{x}+{y}')
            ventana.deiconify()

            estado['id_after'] = root.after(1000, tick)
            root.wait_window(ventana)

        except Exception as e:
            print(f"⚠️  No se pudo mostrar el aviso ({e}). Se aplica la opción por defecto.")

        finally:
            if root_propio and root is not None:
                try:
                    root.destroy()
                except Exception:
                    pass

        return resultado['clave'], resultado['respondio']