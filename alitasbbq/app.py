import customtkinter as ctk
from tkinter import messagebox, filedialog, StringVar, PhotoImage
from PIL import Image
from datetime import datetime, timedelta
from io import BytesIO

from .config import APP_NAME, resource_path
from .db import (
    validar_login,
    obtener_productos,
    agregar_producto,
    actualizar_producto,
    desactivar_producto,
    actualizar_imagen_producto,
    convertir_imagen_a_blob_png,
    obtener_ajuste,
    guardar_ajuste,
    registrar_venta,
    obtener_ventas_dia,
    total_ventas_dia,
    obtener_ventas_rango,
    obtener_resumen_por_dia,
    obtener_resumen_por_metodo,
    anular_venta,
    obtener_venta_por_id,
    obtener_cierre_caja,
    registrar_cierre_caja,
    registrar_cierre_caja_v2,
    obtener_apertura_caja,
    registrar_apertura_caja,
    cerrar_apertura_caja,
    reabrir_caja,
    registrar_movimiento_caja,
    obtener_movimientos_dia,
    resumen_movimientos,
)
from .pdf import generar_pdf_ticket, imprimir_ticket_texto, listar_impresoras, impresora_predeterminada


class AlitasBBQApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1200x800")
        self.resizable(True, True)

        self._logo_image = None
        try:
            icon_path = resource_path("alitasbbq", "assets", "app.ico")
            if icon_path:
                self.iconbitmap(icon_path)
        except Exception:
            try:
                icon_png = resource_path("alitasbbq", "assets", "logo.png")
                self.iconphoto(False, PhotoImage(file=icon_png))
            except Exception:
                pass

        try:
            logo_path = resource_path("alitasbbq", "assets", "logo.png")
            pil_logo = Image.open(logo_path)
            self._logo_image = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(240, 240))
        except Exception:
            try:
                logo_path = resource_path("alitasbbq", "assets", "logo.jpeg")
                pil_logo = Image.open(logo_path)
                self._logo_image = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(240, 240))
            except Exception:
                self._logo_image = None

        self.usuario_actual = None
        self.rol_actual = None
        self.carrito = []
        self._image_cache = {}
        self._placeholder_images = {}
        self._productos_cache = None
        self._productos_cache_dirty = True

        self.color_primary = "#FF6B35"
        self.color_secondary = "#2C3E50"
        self.color_success = "#27AE60"
        self.color_danger = "#E74C3C"

        self.mostrar_login()

    def clear_window(self):
        try:
            self.unbind("<Return>")
        except Exception:
            pass
        try:
            self.unbind("<KP_Enter>")
        except Exception:
            pass
        for widget in self.winfo_children():
            widget.destroy()

    def _get_product_image(self, producto_id, imagen_blob, size):
        cache_key = (producto_id, size)
        cached = self._image_cache.get(cache_key)
        if cached is not None:
            return cached
        if not imagen_blob:
            return self._get_placeholder_image(size)
        try:
            pil_img = Image.open(BytesIO(imagen_blob))
            pil_img.load()
        except Exception:
            return self._get_placeholder_image(size)
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
        self._image_cache[cache_key] = ctk_img
        return ctk_img

    def _get_placeholder_image(self, size):
        cached = self._placeholder_images.get(size)
        if cached is not None:
            return cached
        try:
            from PIL import Image as _Img

            img = _Img.new("RGBA", (256, 256), (52, 73, 94, 255))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
        except Exception:
            ctk_img = None
        self._placeholder_images[size] = ctk_img
        return ctk_img

    def _invalidate_product_image_cache(self, producto_id):
        keys_to_delete = [k for k in self._image_cache.keys() if k[0] == producto_id]
        for k in keys_to_delete:
            del self._image_cache[k]

    def _get_productos(self, force=False):
        if force or self._productos_cache_dirty or self._productos_cache is None:
            self._productos_cache = obtener_productos()
            self._productos_cache_dirty = False
        return self._productos_cache

    def _invalidate_productos_cache(self):
        self._productos_cache = None
        self._productos_cache_dirty = True

    def _asegurar_caja_abierta(self):
        fecha_iso = datetime.now().strftime("%Y-%m-%d")
        cierre = obtener_cierre_caja(fecha_iso, self.usuario_actual)
        cierre_estado = (str(cierre[10]).upper() if (cierre is not None and cierre[10] is not None) else "CERRADA") if cierre is not None else ""
        if cierre is not None and cierre_estado == "CERRADA":
            messagebox.showwarning("Caja cerrada", "La caja de hoy está CERRADA.\n\nNo se puede registrar ventas.")
            self.mostrar_caja()
            return False
        apertura = obtener_apertura_caja(fecha_iso, self.usuario_actual)
        if apertura is not None and str(apertura[4] or "").upper() == "ABIERTA":
            return True
        ok = messagebox.askyesno("Apertura de caja", "No hay caja ABIERTA.\n\n¿Deseas abrir caja para vender?")
        if not ok:
            self.mostrar_caja()
            return False
        dialog = ctk.CTkInputDialog(text="Fondo de caja (S/):", title="Apertura de caja")
        monto_txt = dialog.get_input()
        if monto_txt is None:
            self.mostrar_caja()
            return False
        try:
            monto_inicial = float(str(monto_txt).strip().replace(",", ".") or "0")
        except ValueError:
            messagebox.showerror("Error", "Fondo de caja inválido")
            self.mostrar_caja()
            return False
        if monto_inicial < 0:
            messagebox.showerror("Error", "Fondo de caja inválido")
            self.mostrar_caja()
            return False
        creado = registrar_apertura_caja(fecha_iso, datetime.now().strftime("%H:%M:%S"), self.usuario_actual, monto_inicial)
        if not creado:
            apertura = obtener_apertura_caja(fecha_iso, self.usuario_actual)
            if apertura is None or str(apertura[4] or "").upper() != "ABIERTA":
                messagebox.showwarning("Caja", "No se pudo abrir caja. Revisa el estado en CAJA.")
                self.mostrar_caja()
                return False
        return True

    def mostrar_login(self):
        self.clear_window()

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        if self._logo_image is not None:
            ctk.CTkLabel(frame, text="", image=self._logo_image).pack(pady=(0, 10))

        titulo = ctk.CTkLabel(
            frame,
            text=APP_NAME,
            font=ctk.CTkFont(size=44, weight="bold"),
            text_color=self.color_primary,
        )
        titulo.pack(pady=(0, 10))

        subtitulo = ctk.CTkLabel(frame, text="Sistema de Punto de Venta", font=ctk.CTkFont(size=16))
        subtitulo.pack(pady=(0, 40))

        self.entry_usuario = ctk.CTkEntry(frame, placeholder_text="Usuario", width=300, height=50, font=ctk.CTkFont(size=16))
        self.entry_usuario.pack(pady=10)

        self.entry_clave = ctk.CTkEntry(
            frame,
            placeholder_text="Contraseña",
            show="*",
            width=300,
            height=50,
            font=ctk.CTkFont(size=16),
        )
        self.entry_clave.pack(pady=10)

        btn_login = ctk.CTkButton(
            frame,
            text="INGRESAR",
            width=300,
            height=60,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=self.color_primary,
            hover_color="#E85A2A",
            command=self.login,
        )
        btn_login.pack(pady=30)

        info = ctk.CTkLabel(frame, text="Usuario: admin/caja | Clave: 1234", font=ctk.CTkFont(size=12), text_color="gray")
        info.pack()
        ctk.CTkLabel(frame, text="Desarrollado por SMC Sistemas y Hosting", font=ctk.CTkFont(size=10), text_color="gray").pack(pady=(8, 0))

        self.entry_clave.bind("<Return>", lambda e: self.login())

    def login(self):
        usuario = self.entry_usuario.get()
        clave = self.entry_clave.get()

        resultado = validar_login(usuario, clave)

        if resultado:
            self.usuario_actual = resultado[0]
            self.rol_actual = resultado[1]
            self.mostrar_dashboard()
        else:
            messagebox.showerror("Error", "Usuario o contraseña incorrectos")

    def mostrar_dashboard(self):
        self.clear_window()

        header = ctk.CTkFrame(self, height=80, fg_color=self.color_secondary)
        header.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(header, text=f"{APP_NAME}", font=ctk.CTkFont(size=28, weight="bold"), text_color=self.color_primary).pack(
            side="left", padx=20
        )

        ctk.CTkLabel(
            header,
            text=f"Usuario: {self.usuario_actual} | {datetime.now().strftime('%d/%m/%Y')}",
            font=ctk.CTkFont(size=14),
        ).pack(side="right", padx=20)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        botones = [
            ("🧾 NUEVA VENTA", self.mostrar_ventas, self.color_success, "Registrar ventas"),
            ("📦 PRODUCTOS", self.mostrar_productos, self.color_primary, "Gestionar menú"),
            ("💰 CAJA", self.mostrar_caja, "#3498DB", "Ver caja del día"),
            ("📊 REPORTES", self.mostrar_reportes, "#9B59B6", "Ver reportes"),
            
        ]

        for i, (texto, comando, color, desc) in enumerate(botones):
            frame_btn = ctk.CTkFrame(container, fg_color=color, corner_radius=15)
            frame_btn.grid(row=i // 2, column=i % 2, padx=15, pady=15, sticky="nsew")

            btn = ctk.CTkButton(
                frame_btn,
                text=texto,
                font=ctk.CTkFont(size=32, weight="bold"),
                fg_color="transparent",
                hover_color=color,
                height=200,
                command=comando,
            )
            btn.pack(fill="both", expand=True, padx=5, pady=5)

            ctk.CTkLabel(frame_btn, text=desc, font=ctk.CTkFont(size=14), text_color="white").pack(pady=(0, 10))

        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=1)
        container.grid_rowconfigure(2, weight=1)

        ctk.CTkButton(
            self,
            text="🚪 CERRAR SESIÓN",
            font=ctk.CTkFont(size=16),
            fg_color=self.color_danger,
            hover_color="#C0392B",
            height=50,
            command=self.mostrar_login,
        ).pack(side="bottom", fill="x", padx=20, pady=10)

    def _printer_name(self):
        val = obtener_ajuste("printer_name", None)
        s = str(val).strip() if val is not None else ""
        return s or None

    def mostrar_impresora(self):
        self.clear_window()

        header = ctk.CTkFrame(self, height=80, fg_color=self.color_secondary)
        header.pack(fill="x")


        ctk.CTkButton(
            header,
            text="← VOLVER",
            font=ctk.CTkFont(size=16),
            fg_color=self.color_danger,
            width=150,
            height=50,
            command=self.mostrar_dashboard,
        ).pack(side="right", padx=20)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        card = ctk.CTkFrame(container, fg_color="#2C3E50", corner_radius=15)
        card.pack(fill="x", padx=10, pady=10)

        default_printer = impresora_predeterminada()
        actuales = listar_impresoras()

        ctk.CTkLabel(card, text="CONFIGURACIÓN DE TICKETERA", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.color_primary).pack(
            pady=(15, 8)
        )

        ctk.CTkLabel(
            card,
            text=f"Predeterminada (Windows): {default_printer or '-'}",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        ).pack(pady=(0, 10))

        opciones = ["(Usar predeterminada)"] + list(actuales or [])
        seleccion_actual = self._printer_name()
        if seleccion_actual and seleccion_actual in opciones:
            valor_inicial = seleccion_actual
        else:
            valor_inicial = "(Usar predeterminada)"

        var = StringVar(value=valor_inicial)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(row, text="Impresora:", font=ctk.CTkFont(size=14)).pack(side="left")
        menu = ctk.CTkOptionMenu(row, values=opciones, variable=var, width=520)
        menu.pack(side="left", padx=(10, 0))

        def guardar():
            pick = str(var.get() or "").strip()
            if pick == "(Usar predeterminada)":
                guardar_ajuste("printer_name", "")
            else:
                guardar_ajuste("printer_name", pick)
            messagebox.showinfo("Impresora", "Configuración guardada.")

        def probar():
            printer_name = self._printer_name()
            lineas = [
                f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "Prueba de impresión",
                "Si ves esto, la ticketera está OK",
                "",
                "AlaCrunch",
            ]
            try:
                imprimir_ticket_texto("PRUEBA", lineas, subtitulo=APP_NAME, printer_name=printer_name)
                messagebox.showinfo("Impresión", "Se envió la prueba a la impresora.")
            except Exception as e:
                messagebox.showerror(
                    "Impresión",
                    "No se pudo imprimir.\n\n"
                    "Verifica que la impresora esté instalada en Windows y/o marcada como predeterminada.\n\n"
                    f"Error:\n{e}",
                )

        botones = ctk.CTkFrame(card, fg_color="transparent")
        botones.pack(fill="x", padx=15, pady=(5, 15))

        ctk.CTkButton(botones, text="💾 GUARDAR", fg_color=self.color_success, height=45, command=guardar).pack(side="left", padx=(0, 10))
        ctk.CTkButton(botones, text="🧾 IMPRIMIR PRUEBA", fg_color="#3498DB", height=45, command=probar).pack(side="left")

    def mostrar_ventas(self):
        self.clear_window()
        self.carrito = []

        if not self._asegurar_caja_abierta():
            return

        header = ctk.CTkFrame(self, height=80, fg_color=self.color_secondary)
        header.pack(fill="x")

        ctk.CTkLabel(header, text="🧾 PUNTO DE VENTA", font=ctk.CTkFont(size=28, weight="bold"), text_color=self.color_primary).pack(
            side="left", padx=20
        )

        header_btns = ctk.CTkFrame(header, fg_color="transparent")
        header_btns.pack(side="right", padx=20)

        if self.rol_actual == "admin":
            def _anular_ticket():
                dialog = ctk.CTkInputDialog(text="Ticket / ID de venta:", title="Anular Venta")
                venta_id_txt = dialog.get_input()
                if venta_id_txt is None:
                    return
                try:
                    venta_id = int(str(venta_id_txt).strip())
                except Exception:
                    messagebox.showerror("Error", "ID inválido")
                    return
                if venta_id <= 0:
                    messagebox.showerror("Error", "ID inválido")
                    return
                venta = obtener_venta_por_id(venta_id)
                if not venta:
                    messagebox.showwarning("No encontrado", f"No existe la venta #{venta_id}")
                    return
                _id, fecha, hora, items, total_v, metodo, usuario, anulada, motivo, cliente = venta
                if anulada:
                    messagebox.showinfo("Anulada", f"La venta #{venta_id} ya está ANULADA.\n\nMotivo: {motivo or '-'}")
                    return
                c = str(cliente or "").strip()
                detalle = str(items or "")
                if c:
                    detalle = f"{detalle}\nCliente: {c}"
                detalle = f"#{venta_id} | {fecha} {hora}\n{detalle}\n\nTotal: S/ {float(total_v):.2f}\nUsuario: {usuario}\nMétodo: {metodo}"
                ok = messagebox.askyesno("Confirmar", f"¿Anular esta venta?\n\n{detalle}")
                if not ok:
                    return
                dialog_m = ctk.CTkInputDialog(text="Motivo de anulación:", title="Anular Venta")
                motivo_local = dialog_m.get_input()
                if motivo_local is None:
                    return
                motivo_local = str(motivo_local).strip()
                if not motivo_local:
                    messagebox.showwarning("Motivo requerido", "Debes ingresar un motivo para anular")
                    return
                anular_venta(venta_id, motivo_local, self.usuario_actual)
                messagebox.showinfo("OK", f"Venta #{venta_id} anulada.")

            ctk.CTkButton(
                header_btns,
                text="🛑 ANULAR",
                font=ctk.CTkFont(size=16),
                fg_color=self.color_danger,
                width=150,
                height=50,
                command=_anular_ticket,
            ).pack(side="right", padx=(0, 10))

        ctk.CTkButton(
            header_btns,
            text="← VOLVER",
            font=ctk.CTkFont(size=16),
            fg_color=self.color_danger,
            width=150,
            height=50,
            command=self.mostrar_dashboard,
        ).pack(side="right")

        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        left_panel = ctk.CTkFrame(main_container, fg_color="#2C3E50")
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ctk.CTkLabel(left_panel, text="MENÚ DE PRODUCTOS", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)

        productos_scroll = ctk.CTkScrollableFrame(left_panel, fg_color="transparent")
        productos_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        productos = self._get_productos()
        categoria_actual = None
        grid_frame = None
        grid_index = 0

        for producto in productos:
            prod_id, nombre, categoria, precio, imagen = producto

            if categoria != categoria_actual:
                categoria_actual = categoria
                ctk.CTkLabel(
                    productos_scroll,
                    text=f"═══ {categoria.upper()} ═══",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color=self.color_primary,
                ).pack(pady=(15, 5))
                grid_frame = ctk.CTkFrame(productos_scroll, fg_color="transparent")
                grid_frame.pack(fill="x", padx=5, pady=(0, 10))
                for col in range(3):
                    grid_frame.grid_columnconfigure(col, weight=1)
                grid_index = 0

            producto_img = self._get_product_image(prod_id, imagen, (92, 92))

            btn_producto = ctk.CTkButton(
                grid_frame,
                text=f"{nombre}\nS/ {precio:.2f}",
                font=ctk.CTkFont(size=15, weight="bold"),
                height=170,
                fg_color="#34495E",
                hover_color=self.color_primary,
                image=producto_img,
                compound="top",
                command=lambda p=(nombre, precio): self.agregar_al_carrito(p),
            )
            btn_producto.grid(row=grid_index // 3, column=grid_index % 3, padx=6, pady=6, sticky="nsew")
            grid_index += 1

        right_panel = ctk.CTkFrame(main_container, fg_color="#34495E", width=400)
        right_panel.pack(side="right", fill="both", padx=(10, 0))
        right_panel.pack_propagate(False)

        ctk.CTkLabel(
            right_panel,
            text="🛒 CARRITO DE COMPRA",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.color_primary,
        ).pack(pady=(15, 10))

        self.carrito_frame = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        self.carrito_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        bottom_controls = ctk.CTkFrame(right_panel, fg_color="#2C3E50")
        bottom_controls.pack(side="bottom", fill="x", padx=10, pady=10)
        bottom_controls.grid_columnconfigure(0, weight=1)
        bottom_controls.grid_columnconfigure(1, weight=1)

        self.label_total = ctk.CTkLabel(
            bottom_controls,
            text="TOTAL: S/ 0.00",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=self.color_success,
        )
        self.label_total.grid(row=0, column=0, columnspan=2, padx=10, pady=(12, 10), sticky="nsew")

        self.metodo_pago_var = StringVar(value="Efectivo")
        ctk.CTkLabel(bottom_controls, text="Método:", font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=10, pady=(0, 8), sticky="w")

        self.metodo_menu = ctk.CTkOptionMenu(
            bottom_controls,
            values=["Efectivo", "Tarjeta", "QR"],
            variable=self.metodo_pago_var,
            height=36,
            width=180,
        )
        self.metodo_menu.grid(row=1, column=1, padx=10, pady=(0, 8), sticky="e")

        ctk.CTkLabel(bottom_controls, text="Cliente:", font=ctk.CTkFont(size=14)).grid(row=2, column=0, padx=10, pady=(0, 6), sticky="w")
        cliente_row = ctk.CTkFrame(bottom_controls, fg_color="transparent")
        cliente_row.grid(row=2, column=1, padx=10, pady=(0, 6), sticky="e")

        self.entry_cliente = ctk.CTkEntry(cliente_row, width=118, height=36)
        self.entry_cliente.pack(side="left", padx=(0, 6))

        def _agregar_cliente():
            dialog = ctk.CTkInputDialog(text="Nombre del cliente:", title="Cliente")
            nombre = dialog.get_input()
            if nombre is None:
                return
            nombre = str(nombre).strip()
            if not nombre:
                return
            self.entry_cliente.delete(0, "end")
            self.entry_cliente.insert(0, nombre)
            try:
                self.entry_cliente.focus_set()
            except Exception:
                pass

        ctk.CTkButton(
            cliente_row,
            text="➕",
            width=36,
            height=36,
            fg_color="#3498DB",
            command=_agregar_cliente,
        ).pack(side="left")

        ctk.CTkLabel(bottom_controls, text="Recibido:", font=ctk.CTkFont(size=14)).grid(row=3, column=0, padx=10, pady=(0, 6), sticky="w")
        self.entry_monto_recibido = ctk.CTkEntry(bottom_controls, width=160, height=36)
        self.entry_monto_recibido.grid(row=3, column=1, padx=10, pady=(0, 6), sticky="e")
        self.entry_monto_recibido.bind("<KeyRelease>", self.actualizar_vuelto)

        ctk.CTkLabel(bottom_controls, text="Vuelto:", font=ctk.CTkFont(size=14)).grid(row=4, column=0, padx=10, pady=(0, 10), sticky="w")
        self.label_vuelto = ctk.CTkLabel(bottom_controls, text="S/ 0.00", font=ctk.CTkFont(size=16), text_color=self.color_success)
        self.label_vuelto.grid(row=4, column=1, padx=10, pady=(0, 10), sticky="e")

        ctk.CTkLabel(bottom_controls, text="Delivery:", font=ctk.CTkFont(size=12), text_color="gray").grid(
            row=5, column=0, padx=10, pady=(0, 10), sticky="w"
        )
        self.entry_delivery = ctk.CTkEntry(bottom_controls, width=160, height=32)
        self.entry_delivery.insert(0, "0")
        self.entry_delivery.grid(row=5, column=1, padx=10, pady=(0, 10), sticky="e")
        self.entry_delivery.bind("<KeyRelease>", self.actualizar_totales)

        def on_metodo_change(_val=None):
            metodo_sel = self.metodo_pago_var.get()
            if metodo_sel == "Efectivo":
                self.entry_monto_recibido.configure(state="normal")
                self.actualizar_vuelto()
            else:
                self.entry_monto_recibido.delete(0, "end")
                self.entry_monto_recibido.configure(state="disabled")
                self.label_vuelto.configure(text="-", text_color="gray")

        self.metodo_menu.configure(command=on_metodo_change)
        on_metodo_change()

        btn_limpiar = ctk.CTkButton(
            bottom_controls,
            text="🗑️ LIMPIAR",
            font=ctk.CTkFont(size=16),
            fg_color=self.color_danger,
            height=52,
            command=self.limpiar_carrito,
        )
        btn_limpiar.grid(row=6, column=0, padx=(10, 6), pady=(0, 10), sticky="nsew")

        btn_cobrar = ctk.CTkButton(
            bottom_controls,
            text="💳 COBRAR",
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=self.color_success,
            height=52,
            command=self.procesar_venta,
        )
        btn_cobrar.grid(row=6, column=1, padx=(6, 10), pady=(0, 10), sticky="nsew")

        def _cobrar_hotkey(_event=None):
            self.procesar_venta()
            return "break"

        self.bind("<Return>", _cobrar_hotkey)
        self.bind("<KP_Enter>", _cobrar_hotkey)

    def agregar_al_carrito(self, producto):
        nombre, precio = producto
        self.carrito.append({"nombre": nombre, "precio": precio, "cantidad": 1})
        self.actualizar_carrito()

    def _delivery_monto(self):
        if not hasattr(self, "entry_delivery"):
            return 0.0
        try:
            texto = self.entry_delivery.get().strip().replace(",", ".")
        except Exception:
            return 0.0
        if not texto:
            return 0.0
        try:
            monto = float(texto)
        except ValueError:
            return 0.0
        return monto if monto > 0 else 0.0

    def _calcular_total_carrito(self):
        subtotal = sum(item["precio"] for item in self.carrito)
        return float(subtotal) + float(self._delivery_monto())

    def actualizar_totales(self, event=None):
        if not hasattr(self, "label_total"):
            return
        total = self._calcular_total_carrito()
        self.label_total.configure(text=f"TOTAL: S/ {total:.2f}")
        if hasattr(self, "entry_monto_recibido") and hasattr(self, "label_vuelto"):
            if hasattr(self, "metodo_pago_var") and self.metodo_pago_var.get() != "Efectivo":
                self.label_vuelto.configure(text="-", text_color="gray")
            else:
                self.actualizar_vuelto()

    def actualizar_carrito(self):
        for widget in self.carrito_frame.winfo_children():
            widget.destroy()

        for i, item in enumerate(self.carrito):
            frame_item = ctk.CTkFrame(self.carrito_frame, fg_color="#2C3E50")
            frame_item.pack(fill="x", pady=5)

            ctk.CTkLabel(frame_item, text=item["nombre"], font=ctk.CTkFont(size=14, weight="bold"), anchor="w").pack(side="left", padx=10, pady=10)

            ctk.CTkLabel(frame_item, text=f"S/ {item['precio']:.2f}", font=ctk.CTkFont(size=14), text_color=self.color_success).pack(
                side="right", padx=10
            )

            btn_eliminar = ctk.CTkButton(
                frame_item,
                text="✖",
                width=30,
                height=30,
                fg_color=self.color_danger,
                command=lambda idx=i: self.eliminar_item(idx),
            )
            btn_eliminar.pack(side="right", padx=5)
        self.actualizar_totales()

    def eliminar_item(self, index):
        if 0 <= index < len(self.carrito):
            self.carrito.pop(index)
            self.actualizar_carrito()

    def limpiar_carrito(self):
        if self.carrito:
            ok = messagebox.askyesno("Confirmar", "¿Seguro de limpiar el carrito?")
            if not ok:
                return
        self.carrito = []
        self.actualizar_carrito()
        if hasattr(self, "entry_delivery"):
            self.entry_delivery.delete(0, "end")
            self.entry_delivery.insert(0, "0")
        if hasattr(self, "entry_monto_recibido"):
            self.entry_monto_recibido.delete(0, "end")
        if hasattr(self, "entry_cliente"):
            self.entry_cliente.delete(0, "end")
        if hasattr(self, "label_vuelto"):
            if hasattr(self, "metodo_pago_var") and self.metodo_pago_var.get() != "Efectivo":
                self.label_vuelto.configure(text="-", text_color="gray")
            else:
                self.label_vuelto.configure(text="S/ 0.00", text_color=self.color_success)
        self.actualizar_totales()

    def actualizar_vuelto(self, event=None):
        if not hasattr(self, "entry_monto_recibido") or not hasattr(self, "label_vuelto"):
            return
        if hasattr(self, "metodo_pago_var") and self.metodo_pago_var.get() != "Efectivo":
            self.label_vuelto.configure(text="-", text_color="gray")
            return
        total = self._calcular_total_carrito()
        texto = self.entry_monto_recibido.get().strip().replace(",", ".")
        if not texto:
            self.label_vuelto.configure(text="S/ 0.00", text_color=self.color_success)
            return
        try:
            recibido = float(texto)
        except ValueError:
            self.label_vuelto.configure(text="S/ 0.00", text_color=self.color_success)
            return
        diferencia = recibido - total
        if diferencia < 0:
            self.label_vuelto.configure(text=f"Falta: S/ {abs(diferencia):.2f}", text_color=self.color_danger)
        else:
            self.label_vuelto.configure(text=f"S/ {diferencia:.2f}", text_color=self.color_success)

    def procesar_venta(self):
        if not self.carrito:
            messagebox.showwarning("Carrito vacío", "Agrega productos al carrito")
            return

        if not self._asegurar_caja_abierta():
            return

        ahora = datetime.now()
        cliente = ""
        if hasattr(self, "entry_cliente"):
            try:
                cliente = str(self.entry_cliente.get() or "").strip()
            except Exception:
                cliente = ""
        delivery = self._delivery_monto()
        total = self._calcular_total_carrito()
        items_list = [f"{item['nombre']}" for item in self.carrito]
        if delivery > 0:
            items_list.append(f"Delivery S/ {delivery:.2f}")
        items_str = ", ".join(items_list)

        metodo = "Efectivo"
        if hasattr(self, "metodo_pago_var"):
            try:
                metodo_val = self.metodo_pago_var.get()
                if metodo_val:
                    metodo = metodo_val
            except Exception:
                metodo = "Efectivo"

        mensaje_vuelto = ""
        recibido = None
        cambio = None
        if metodo == "Efectivo":
            if not hasattr(self, "entry_monto_recibido"):
                messagebox.showwarning("Datos incompletos", "No se encontró el campo de monto recibido")
                return
            texto = self.entry_monto_recibido.get().strip().replace(",", ".")
            if not texto:
                messagebox.showwarning("Monto recibido", "Ingresa el monto recibido")
                return
            try:
                recibido = float(texto)
            except ValueError:
                messagebox.showerror("Error", "Monto recibido inválido")
                return
            if recibido < total:
                messagebox.showwarning("Monto insuficiente", f"El monto recibido es menor al total (S/ {total:.2f})")
                return
            cambio = recibido - total
            mensaje_vuelto = f"\nRecibido: S/ {recibido:.2f}\nVuelto: S/ {cambio:.2f}"

        venta_id = registrar_venta(items_str, total, self.usuario_actual, metodo, cliente or None)
        ticket_num = f"T-{int(venta_id):04d}"
        try:
            lineas = []
            lineas.append(f"Fecha: {ahora.strftime('%Y-%m-%d %H:%M:%S')}")
            lineas.append(f"Ticket: {ticket_num}")
            if cliente:
                lineas.append(f"Cliente: {cliente}")
            lineas.append(f"Usuario: {self.usuario_actual}")
            lineas.append(f"Método: {metodo}")
            lineas.append("")
            lineas.append("Detalle:")
            for item in self.carrito:
                nombre = str(item.get("nombre", "")).strip()
                cantidad = int(item.get("cantidad", 1) or 1)
                precio = float(item.get("precio", 0) or 0)
                if nombre:
                    pref = f"{cantidad}x " if cantidad > 1 else ""
                    lineas.append(f"- {pref}{nombre}  S/ {precio:.2f}")
            if float(delivery or 0) > 0:
                lineas.append(f"- Delivery  S/ {float(delivery):.2f}")
            lineas.append("")
            lineas.append(f"TOTAL: S/ {float(total):.2f}")
            if recibido is not None and cambio is not None:
                lineas.append(f"Recibido: S/ {float(recibido):.2f}")
                lineas.append(f"Vuelto: S/ {float(cambio):.2f}")

            imprimir_ticket_texto("TICKET DE COMPRA", lineas, subtitulo=APP_NAME, printer_name=self._printer_name())
        except Exception as e:
            messagebox.showwarning(
                "Ticket",
                "La venta se registró, pero no se pudo imprimir el ticket.\n\n"
                "Revisa que la ticketera esté instalada y marcada como predeterminada en Windows.\n\n"
                f"{e}",
            )

        messagebox.showinfo(
            "Venta exitosa",
            f"Venta registrada por S/ {total:.2f}\nTicket: {ticket_num}\nMétodo: {metodo}{mensaje_vuelto}\n\nGracias por su compra! 🍗",
        )

        self.limpiar_carrito()
        if hasattr(self, "entry_monto_recibido"):
            self.entry_monto_recibido.delete(0, "end")
        if hasattr(self, "label_vuelto"):
            if hasattr(self, "metodo_pago_var") and self.metodo_pago_var.get() != "Efectivo":
                self.label_vuelto.configure(text="-", text_color="gray")
            else:
                self.label_vuelto.configure(text="S/ 0.00", text_color=self.color_success)

    def mostrar_productos(self):
        self.clear_window()

        solo_lectura = self.rol_actual == "cajero"

        header = ctk.CTkFrame(self, height=80, fg_color=self.color_secondary)
        header.pack(fill="x")

        ctk.CTkLabel(header, text="📦 GESTIÓN DE PRODUCTOS", font=ctk.CTkFont(size=28, weight="bold"), text_color=self.color_primary).pack(
            side="left", padx=20
        )

        ctk.CTkButton(
            header,
            text="← VOLVER",
            font=ctk.CTkFont(size=16),
            fg_color=self.color_danger,
            width=150,
            height=50,
            command=self.mostrar_dashboard,
        ).pack(side="right", padx=20)

        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        if not solo_lectura:
            form_frame = ctk.CTkFrame(container, fg_color="#2C3E50")
            form_frame.pack(fill="x", pady=(0, 20))

            ctk.CTkLabel(form_frame, text="AGREGAR NUEVO PRODUCTO", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=15)

            inputs_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
            inputs_frame.pack(padx=20, pady=10)

            ctk.CTkLabel(inputs_frame, text="Nombre:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=10, pady=5, sticky="e")
            entry_nombre = ctk.CTkEntry(inputs_frame, width=250, height=40)
            entry_nombre.grid(row=0, column=1, padx=10, pady=5)

            ctk.CTkLabel(inputs_frame, text="Categoría:", font=ctk.CTkFont(size=14)).grid(row=0, column=2, padx=10, pady=5, sticky="e")
            entry_categoria = ctk.CTkEntry(inputs_frame, width=200, height=40)
            entry_categoria.grid(row=0, column=3, padx=10, pady=5)

            ctk.CTkLabel(inputs_frame, text="Precio:", font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=10, pady=5, sticky="e")
            entry_precio = ctk.CTkEntry(inputs_frame, width=150, height=40)
            entry_precio.grid(row=1, column=1, padx=10, pady=5, sticky="w")

            imagen_blob_seleccionada = {"blob": None, "preview": None}

            ctk.CTkLabel(inputs_frame, text="Imagen:", font=ctk.CTkFont(size=14)).grid(row=1, column=2, padx=10, pady=5, sticky="e")
            btn_imagen = ctk.CTkButton(inputs_frame, text="Seleccionar", width=200, height=40, fg_color="#3498DB")
            btn_imagen.grid(row=1, column=3, padx=10, pady=5, sticky="w")

            label_preview = ctk.CTkLabel(inputs_frame, text="Sin imagen", width=200, height=80, fg_color="#34495E")
            label_preview.grid(row=2, column=3, padx=10, pady=(5, 10), sticky="w")

            def seleccionar_imagen_para_nuevo():
                file_path = filedialog.askopenfilename(
                    title="Seleccionar imagen",
                    filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"), ("Todos", "*.*")],
                )
                if not file_path:
                    return
                try:
                    blob = convertir_imagen_a_blob_png(file_path)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{e}")
                    return
                imagen_blob_seleccionada["blob"] = blob
                try:
                    pil_img = Image.open(BytesIO(blob))
                    pil_img.load()
                    preview_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(80, 80))
                    imagen_blob_seleccionada["preview"] = preview_img
                    label_preview.configure(image=preview_img, text="")
                except Exception:
                    imagen_blob_seleccionada["preview"] = None
                    label_preview.configure(image=None, text="Imagen cargada")

            btn_imagen.configure(command=seleccionar_imagen_para_nuevo)

            def guardar_producto():
                try:
                    nombre = entry_nombre.get()
                    categoria = entry_categoria.get()
                    precio = float(entry_precio.get())

                    if nombre and categoria and precio > 0:
                        agregar_producto(nombre, categoria, precio, imagen_blob_seleccionada["blob"])
                        self._invalidate_productos_cache()
                        messagebox.showinfo("Éxito", "Producto agregado correctamente")
                        entry_nombre.delete(0, "end")
                        entry_categoria.delete(0, "end")
                        entry_precio.delete(0, "end")
                        imagen_blob_seleccionada["blob"] = None
                        imagen_blob_seleccionada["preview"] = None
                        label_preview.configure(image=None, text="Sin imagen")
                        actualizar_lista()
                    else:
                        messagebox.showwarning("Error", "Completa todos los campos")
                except ValueError:
                    messagebox.showerror("Error", "Precio inválido")

            ctk.CTkButton(
                form_frame,
                text="➕ AGREGAR PRODUCTO",
                font=ctk.CTkFont(size=16, weight="bold"),
                fg_color=self.color_success,
                height=50,
                width=300,
                command=guardar_producto,
            ).pack(pady=15)

        lista_frame = ctk.CTkFrame(container, fg_color="#2C3E50")
        lista_frame.pack(fill="x", expand=True)

        def actualizar_lista():
            for widget in lista_frame.winfo_children():
                widget.destroy()

            ctk.CTkLabel(
                lista_frame,
                text="PRODUCTOS REGISTRADOS",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=self.color_primary,
            ).pack(pady=15)

            productos = self._get_productos(force=True)
            for prod in productos:
                prod_frame = ctk.CTkFrame(lista_frame, fg_color="#34495E")
                prod_frame.pack(fill="x", padx=10, pady=5)

                prod_id, nombre, categoria, precio, imagen = prod
                thumb = self._get_product_image(prod_id, imagen, (50, 50))
                if thumb is not None:
                    ctk.CTkLabel(prod_frame, text="", image=thumb).pack(side="left", padx=(15, 10), pady=10)
                else:
                    ctk.CTkLabel(prod_frame, text=" ", width=52, height=52, fg_color="#2C3E50").pack(side="left", padx=(15, 10), pady=10)

                info_text = f"{nombre} - {categoria} - S/ {precio:.2f}"
                ctk.CTkLabel(prod_frame, text=info_text, font=ctk.CTkFont(size=16), anchor="w").pack(side="left", padx=10, pady=15, fill="x", expand=True)

                if not solo_lectura:
                    def cambiar_imagen(pid=prod_id):
                        file_path = filedialog.askopenfilename(
                            title="Seleccionar imagen",
                            filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"), ("Todos", "*.*")],
                        )
                        if not file_path:
                            return
                        try:
                            blob = convertir_imagen_a_blob_png(file_path)
                        except Exception as e:
                            messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{e}")
                            return
                        actualizar_imagen_producto(pid, blob)
                        self._invalidate_product_image_cache(pid)
                        self._invalidate_productos_cache()
                        actualizar_lista()

                    def borrar_producto(pid=prod_id, nombre_prod=nombre):
                        ok = messagebox.askyesno("Confirmar", f"¿Borrar de la carta este producto?\n\n{nombre_prod}")
                        if not ok:
                            return
                        desactivar_producto(pid)
                        self._invalidate_product_image_cache(pid)
                        self._invalidate_productos_cache()
                        actualizar_lista()

                    def editar_producto_ui(pid=prod_id, n=nombre, c=categoria, p=precio):
                        win = ctk.CTkToplevel(self)
                        win.title("Editar producto")
                        win.geometry("420x330")
                        win.resizable(False, False)
                        win.grab_set()

                        frame = ctk.CTkFrame(win, fg_color="#2C3E50")
                        frame.pack(fill="both", expand=True, padx=15, pady=15)

                        ctk.CTkLabel(frame, text="EDITAR PRODUCTO", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 15))

                        form = ctk.CTkFrame(frame, fg_color="transparent")
                        form.pack(fill="x", padx=10, pady=10)

                        ctk.CTkLabel(form, text="Nombre:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=10, pady=8, sticky="e")
                        entry_n = ctk.CTkEntry(form, width=260, height=40)
                        entry_n.grid(row=0, column=1, padx=10, pady=8, sticky="w")
                        entry_n.insert(0, str(n))

                        ctk.CTkLabel(form, text="Categoría:", font=ctk.CTkFont(size=14)).grid(row=1, column=0, padx=10, pady=8, sticky="e")
                        entry_c = ctk.CTkEntry(form, width=260, height=40)
                        entry_c.grid(row=1, column=1, padx=10, pady=8, sticky="w")
                        entry_c.insert(0, str(c))

                        ctk.CTkLabel(form, text="Precio:", font=ctk.CTkFont(size=14)).grid(row=2, column=0, padx=10, pady=8, sticky="e")
                        entry_p = ctk.CTkEntry(form, width=140, height=40)
                        entry_p.grid(row=2, column=1, padx=10, pady=8, sticky="w")
                        entry_p.insert(0, f"{float(p):.2f}")

                        def guardar_edicion():
                            nombre_nuevo = entry_n.get().strip()
                            categoria_nueva = entry_c.get().strip()
                            try:
                                precio_nuevo = float(entry_p.get())
                            except ValueError:
                                messagebox.showerror("Error", "Precio inválido")
                                return
                            if not nombre_nuevo or not categoria_nueva or precio_nuevo <= 0:
                                messagebox.showwarning("Error", "Completa todos los campos")
                                return
                            actualizar_producto(pid, nombre_nuevo, categoria_nueva, precio_nuevo)
                            self._invalidate_productos_cache()
                            actualizar_lista()
                            win.destroy()

                        botones = ctk.CTkFrame(frame, fg_color="transparent")
                        botones.pack(fill="x", padx=10, pady=(10, 5))
                        ctk.CTkButton(botones, text="GUARDAR", fg_color=self.color_success, height=45, command=guardar_edicion).pack(
                            side="left", expand=True, fill="x", padx=(0, 8)
                        )
                        ctk.CTkButton(botones, text="CANCELAR", fg_color=self.color_danger, height=45, command=win.destroy).pack(
                            side="left", expand=True, fill="x", padx=(8, 0)
                        )

                    ctk.CTkButton(prod_frame, text="✏️", width=45, height=40, fg_color="#9B59B6", command=editar_producto_ui).pack(
                        side="right", padx=5, pady=10
                    )
                    ctk.CTkButton(prod_frame, text="🖼️", width=45, height=40, fg_color="#3498DB", command=cambiar_imagen).pack(
                        side="right", padx=5, pady=10
                    )
                    ctk.CTkButton(prod_frame, text="🗑️", width=45, height=40, fg_color=self.color_danger, command=borrar_producto).pack(
                        side="right", padx=(5, 15), pady=10
                    )

        actualizar_lista()

    def mostrar_caja(self):
        self.clear_window()

        header = ctk.CTkFrame(self, height=80, fg_color=self.color_secondary)
        header.pack(fill="x")

        ctk.CTkLabel(header, text="💰 CAJA DEL DÍA", font=ctk.CTkFont(size=28, weight="bold"), text_color=self.color_primary).pack(
            side="left", padx=20
        )

        ctk.CTkButton(
            header,
            text="← VOLVER",
            font=ctk.CTkFont(size=16),
            fg_color=self.color_danger,
            width=150,
            height=50,
            command=self.mostrar_dashboard,
        ).pack(side="right", padx=20)

        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        total_frame = ctk.CTkFrame(container, fg_color=self.color_success, height=200)
        total_frame.pack(fill="x", pady=(0, 20))
        total_frame.pack_propagate(False)

        fecha_hoy = datetime.now()
        fecha_iso = fecha_hoy.strftime("%Y-%m-%d")
        apertura = obtener_apertura_caja(fecha_iso, self.usuario_actual)
        cierre = obtener_cierre_caja(fecha_iso, self.usuario_actual)
        cierre_estado = (str(cierre[10]).upper() if (cierre is not None and cierre[10] is not None) else "CERRADA") if cierre is not None else ""
        caja_cerrada = cierre is not None and cierre_estado == "CERRADA"
        apertura_abierta = apertura is not None and str(apertura[4] or "").upper() == "ABIERTA"

        ctk.CTkLabel(total_frame, text=f"📅 {fecha_hoy.strftime('%d/%m/%Y')}", font=ctk.CTkFont(size=20)).pack(pady=(30, 10))

        filtro_usuario_ventas = None if self.rol_actual == "admin" else self.usuario_actual
        total = total_ventas_dia(filtro_usuario_ventas)
        ctk.CTkLabel(total_frame, text=f"S/ {total:.2f}", font=ctk.CTkFont(size=60, weight="bold")).pack()

        ctk.CTkLabel(total_frame, text="Total del Día", font=ctk.CTkFont(size=18)).pack()

        if caja_cerrada:
            estado_txt = "CERRADA"
            estado_color = self.color_danger
        elif cierre_estado == "REABIERTA":
            estado_txt = "REABIERTA"
            estado_color = "#F1C40F"
        else:
            estado_txt = "ABIERTA" if apertura_abierta else "SIN APERTURA"
            estado_color = "#3498DB" if apertura_abierta else "#F1C40F"
        ctk.CTkLabel(total_frame, text=f"Estado: {estado_txt}", font=ctk.CTkFont(size=14, weight="bold"), text_color=estado_color).pack(
            pady=(5, 0)
        )
        if apertura:
            _, hora_ap, _, monto_ini, _, _ = apertura
            ctk.CTkLabel(
                total_frame,
                text=f"Apertura: {hora_ap} | Inicial: S/ {float(monto_ini or 0):.2f}",
                font=ctk.CTkFont(size=12),
                text_color="white",
            ).pack(pady=(3, 0))

        def _norm_metodo(metodo):
            s = str(metodo or "").strip().lower()
            if s == "efectivo":
                return "Efectivo"
            if s == "tarjeta":
                return "Tarjeta"
            if s in {"qr", "yape/plin", "yape", "plin", "qr (yape/plin)"}:
                return "QR"
            return str(metodo or "Sin método")

        def _totales_caja():
            ventas_local = obtener_ventas_rango(fecha_iso, fecha_iso, self.usuario_actual)
            total_dia = sum(float(v[4]) for v in ventas_local) if ventas_local else 0.0

            resumen_metodo = obtener_resumen_por_metodo(fecha_iso, fecha_iso, self.usuario_actual)
            total_efectivo = 0.0
            total_tarjeta = 0.0
            total_qr = 0.0
            ventas_count = 0
            for metodo, cant, tot in resumen_metodo:
                ventas_count += int(cant)
                m = _norm_metodo(metodo)
                if m == "Efectivo":
                    total_efectivo += float(tot)
                elif m == "Tarjeta":
                    total_tarjeta += float(tot)
                elif m == "QR":
                    total_qr += float(tot)

            apertura_local = obtener_apertura_caja(fecha_iso, self.usuario_actual)
            monto_apertura = float(apertura_local[3] or 0) if apertura_local else 0.0
            total_ingresos, total_egresos = resumen_movimientos(fecha_iso, fecha_iso, self.usuario_actual)
            efectivo_esperado = monto_apertura + total_efectivo + float(total_ingresos) - float(total_egresos)

            return (
                ventas_local,
                resumen_metodo,
                total_dia,
                ventas_count,
                total_efectivo,
                total_tarjeta,
                total_qr,
                float(total_ingresos),
                float(total_egresos),
                monto_apertura,
                efectivo_esperado,
            )

        def reporte_x_pdf():
            apertura_local = obtener_apertura_caja(fecha_iso, self.usuario_actual)
            if apertura_local is None or str(apertura_local[4] or "").upper() != "ABIERTA":
                messagebox.showwarning("Caja", "No hay caja ABIERTA.\n\nAbre caja para generar el Reporte X.")
                return

            sugerido = f"reporte_x_{fecha_iso}_{datetime.now().strftime('%H%M%S')}.pdf"
            file_path = filedialog.asksaveasfilename(
                title="Guardar Reporte X (PDF)",
                defaultextension=".pdf",
                initialfile=sugerido,
                filetypes=[("PDF", "*.pdf")],
            )
            if not file_path:
                return

            ventas_local, resumen_metodo, total_dia, ventas_count, total_ef, total_tar, total_qr, ing, egr, fondo, efectivo_esp = _totales_caja()
            movs = obtener_movimientos_dia(self.usuario_actual)

            lineas = []
            lineas.append(f"Fecha: {fecha_iso}")
            lineas.append(f"Usuario: {self.usuario_actual}")
            lineas.append("")
            lineas.append("Ventas:")
            lineas.append(f"- Efectivo: S/ {total_ef:.2f}")
            lineas.append(f"- Tarjeta: S/ {total_tar:.2f}")
            lineas.append(f"- QR: S/ {total_qr:.2f}")
            lineas.append(f"- Total: S/ {total_dia:.2f}")
            lineas.append("")
            lineas.append("Caja (efectivo):")
            lineas.append(f"- Fondo inicial: S/ {fondo:.2f}")
            lineas.append(f"- Ingresos: S/ {ing:.2f}")
            lineas.append(f"- Egresos: S/ {egr:.2f}")
            lineas.append(f"- Efectivo esperado: S/ {efectivo_esp:.2f}")
            lineas.append("")
            lineas.append("Movimientos:")
            if movs:
                for _, _, hora, tipo, monto, desc, _u in movs:
                    d = (str(desc).strip() if desc is not None else "")
                    if d:
                        lineas.append(f"{hora} | {tipo} | S/ {float(monto):.2f} | {d}")
                    else:
                        lineas.append(f"{hora} | {tipo} | S/ {float(monto):.2f}")
            else:
                lineas.append("- Sin movimientos")

            try:
                generar_pdf_ticket(file_path, "REPORTE X", lineas, subtitulo="LECTURA PARCIAL")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}")
                return

            messagebox.showinfo("Reporte X", f"PDF generado:\n{file_path}")

        def cerrar_caja_pdf():
            ventas_local, resumen_metodo, total_dia, ventas_count, total_ef, total_tar, total_qr, ing, egr, fondo, efectivo_esp = _totales_caja()
            if not ventas_local:
                ok = messagebox.askyesno("Sin ventas", "No hay ventas registradas hoy.\n\n¿Cerrar caja y generar el PDF igual?")
                if not ok:
                    return

            cierre_local = obtener_cierre_caja(fecha_iso, self.usuario_actual)
            cierre_estado_local = (str(cierre_local[10]).upper() if (cierre_local is not None and cierre_local[10] is not None) else "CERRADA") if cierre_local is not None else ""
            registrar_cierre = cierre_local is None or cierre_estado_local != "CERRADA"
            if cierre_local is not None and cierre_estado_local == "CERRADA":
                messagebox.showinfo("Caja cerrada", "La caja de hoy ya fue cerrada para este usuario")
                return

            apertura_local = obtener_apertura_caja(fecha_iso, self.usuario_actual)
            if apertura_local is None or str(apertura_local[4] or "").upper() != "ABIERTA":
                ok = messagebox.askyesno("Apertura requerida", "No hay caja abierta hoy.\n\n¿Abrir caja y continuar?")
                if not ok:
                    return
                dialog = ctk.CTkInputDialog(text="Fondo de caja (S/):", title="Apertura de caja")
                monto_txt = dialog.get_input()
                if monto_txt is None:
                    return
                try:
                    monto_inicial = float(str(monto_txt).strip().replace(",", ".") or "0")
                except ValueError:
                    messagebox.showerror("Error", "Fondo de caja inválido")
                    return
                if monto_inicial < 0:
                    messagebox.showerror("Error", "Fondo de caja inválido")
                    return
                registrar_apertura_caja(fecha_iso, datetime.now().strftime("%H:%M:%S"), self.usuario_actual, monto_inicial)
                ventas_local, resumen_metodo, total_dia, ventas_count, total_ef, total_tar, total_qr, ing, egr, fondo, efectivo_esp = _totales_caja()

            ok = messagebox.askyesno("Confirmar", "¿Seguro de cerrar caja (Corte Z) y generar el PDF?")
            if not ok:
                return

            efectivo_contado = None
            diferencia_efectivo = None
            fondo_manana = None
            a_retirar = None
            if registrar_cierre:
                dialog = ctk.CTkInputDialog(text="Conteo físico de efectivo total (S/):", title="Corte Z")
                contado_txt = dialog.get_input()
                if contado_txt is None:
                    return
                try:
                    efectivo_contado = float(str(contado_txt).strip().replace(",", ".") or "0")
                except ValueError:
                    messagebox.showerror("Error", "Conteo físico inválido")
                    return
                diferencia_efectivo = float(efectivo_contado) - float(efectivo_esp)
                dialog = ctk.CTkInputDialog(
                    text=f"Fondo para mañana (S/) (sugerido S/ {float(fondo):.2f}):",
                    title="Corte Z",
                )
                fondo_txt = dialog.get_input()
                if fondo_txt is None:
                    return
                fondo_txt = str(fondo_txt).strip()
                if not fondo_txt:
                    fondo_manana = float(fondo)
                else:
                    try:
                        fondo_manana = float(fondo_txt.replace(",", ".") or "0")
                    except ValueError:
                        messagebox.showerror("Error", "Fondo para mañana inválido")
                        return
                if float(fondo_manana) < 0:
                    messagebox.showerror("Error", "Fondo para mañana inválido")
                    return
                a_retirar = float(efectivo_contado) - float(fondo_manana)

            sugerido = f"corte_z_{fecha_iso}_{datetime.now().strftime('%H%M%S')}.pdf"
            file_path = filedialog.asksaveasfilename(
                title="Guardar Corte Z (PDF)",
                defaultextension=".pdf",
                initialfile=sugerido,
                filetypes=[("PDF", "*.pdf")],
            )
            if not file_path:
                return

            movs = obtener_movimientos_dia(self.usuario_actual)

            igv_rate = 0.18
            base_imp = float(total_dia) / (1.0 + igv_rate) if float(total_dia) > 0 else 0.0
            igv_total = float(total_dia) - float(base_imp)

            productos = self._get_productos()
            nombre_a_categoria = {str(n): str(c) for _pid, n, c, _p, _i in productos}
            conteo_items = {}
            conteo_categorias = {}
            for _idv, _fv, _hv, items_txt, _tv, _uv, _mv, anulada, _motivo in ventas_local:
                if anulada:
                    continue
                for it in str(items_txt or "").split(","):
                    nombre_it = str(it).strip()
                    if not nombre_it:
                        continue
                    conteo_items[nombre_it] = int(conteo_items.get(nombre_it, 0)) + 1
                    cat = nombre_a_categoria.get(nombre_it) or "Sin categoría"
                    conteo_categorias[cat] = int(conteo_categorias.get(cat, 0)) + 1

            lineas = []
            lineas.append(f"Fecha: {fecha_iso}")
            lineas.append(f"Usuario: {self.usuario_actual}")
            lineas.append("Estado: CERRADA")
            lineas.append("")
            lineas.append("Ventas:")
            lineas.append(f"- Efectivo: S/ {total_ef:.2f}")
            lineas.append(f"- Tarjeta: S/ {total_tar:.2f}")
            lineas.append(f"- QR: S/ {total_qr:.2f}")
            lineas.append(f"- Total: S/ {total_dia:.2f}")
            lineas.append(f"- Ventas (tickets): {int(ventas_count)}")
            lineas.append("")
            lineas.append("Impuestos (IGV 18%):")
            lineas.append(f"- Base imponible: S/ {float(base_imp):.2f}")
            lineas.append(f"- IGV total: S/ {float(igv_total):.2f}")
            lineas.append("")
            lineas.append("Caja (efectivo):")
            lineas.append(f"- Fondo inicial: S/ {fondo:.2f}")
            lineas.append(f"- Ingresos: S/ {ing:.2f}")
            lineas.append(f"- Egresos: S/ {egr:.2f}")
            lineas.append(f"- Efectivo esperado: S/ {efectivo_esp:.2f}")
            if registrar_cierre:
                lineas.append(f"- Conteo físico: S/ {float(efectivo_contado):.2f}")
                lineas.append(f"- Diferencia: S/ {float(diferencia_efectivo):.2f}")
                lineas.append(f"- Fondo mañana: S/ {float(fondo_manana):.2f}")
                lineas.append(f"- A retirar: S/ {float(a_retirar):.2f}")
            lineas.append("")
            if conteo_items:
                lineas.append("Lo más vendido:")
                top_items = sorted(conteo_items.items(), key=lambda x: (-int(x[1]), str(x[0])))[:10]
                for nombre_it, cant_it in top_items:
                    lineas.append(f"- {nombre_it}: {int(cant_it)}")
                lineas.append("")
            if conteo_categorias:
                lineas.append("Por categoría:")
                top_cat = sorted(conteo_categorias.items(), key=lambda x: (-int(x[1]), str(x[0])))
                for cat, cant_cat in top_cat:
                    lineas.append(f"- {cat}: {int(cant_cat)}")
                lineas.append("")
            lineas.append("Movimientos:")
            if movs:
                for _, _, hora, tipo, monto, desc, _u in movs:
                    d = (str(desc).strip() if desc is not None else "")
                    if d:
                        lineas.append(f"{hora} | {tipo} | S/ {float(monto):.2f} | {d}")
                    else:
                        lineas.append(f"{hora} | {tipo} | S/ {float(monto):.2f}")
            else:
                lineas.append("- Sin movimientos")
            lineas.append("")
            incluir_detalle = len([v for v in ventas_local if not v[7]]) <= 40
            if incluir_detalle:
                lineas.append("Ventas del día:")
                for venta_id, _, hora, items, total_v, usuario, metodo, anulada, motivo in ventas_local:
                    if anulada:
                        continue
                    ticket = f"T-{int(venta_id):04d}"
                    lineas.append(f"{hora} | {ticket} | {_norm_metodo(metodo)} | S/ {float(total_v):.2f} | {items}")
            else:
                lineas.append("Ventas del día:")
                lineas.append(f"- Detalle omitido (tickets: {int(ventas_count)})")

            try:
                generar_pdf_ticket(file_path, "CORTE Z", lineas, subtitulo="CIERRE DE CAJA")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}")
                return

            if registrar_cierre:
                registrar_cierre_caja_v2(
                    fecha=fecha_iso,
                    hora=datetime.now().strftime("%H:%M:%S"),
                    total=total_dia,
                    usuario=self.usuario_actual,
                    archivo_pdf=file_path,
                    total_efectivo=total_ef,
                    total_yape=total_qr,
                    ventas_count=ventas_count,
                    efectivo_contado=efectivo_contado,
                    diferencia_efectivo=diferencia_efectivo,
                    total_tarjeta=total_tar,
                    total_qr=total_qr,
                    total_ingresos=ing,
                    total_egresos=egr,
                    monto_apertura=fondo,
                    efectivo_esperado=efectivo_esp,
                )
                cerrar_apertura_caja(fecha_iso, self.usuario_actual, datetime.now().strftime("%H:%M:%S"))
            if registrar_cierre:
                messagebox.showinfo(
                    "Cierre de caja",
                    "Corte Z generado.\n\n"
                    f"Efectivo esperado: S/ {float(efectivo_esp):.2f}\n"
                    f"Conteo físico: S/ {float(efectivo_contado):.2f}\n"
                    f"Diferencia: S/ {float(diferencia_efectivo):.2f}\n\n"
                    f"Fondo mañana: S/ {float(fondo_manana):.2f}\n"
                    f"A retirar: S/ {float(a_retirar):.2f}\n\n"
                    f"PDF:\n{file_path}",
                )
            else:
                messagebox.showinfo("Cierre de caja", f"PDF generado:\n{file_path}")
            self.mostrar_caja()

        acciones = ctk.CTkFrame(container, fg_color="transparent")
        acciones.pack(fill="x", pady=(0, 10))

        def abrir_caja():
            cierre_local = obtener_cierre_caja(fecha_iso, self.usuario_actual)
            cierre_estado_local = (str(cierre_local[10]).upper() if (cierre_local is not None and cierre_local[10] is not None) else "CERRADA") if cierre_local is not None else ""
            if cierre_local is not None and cierre_estado_local == "CERRADA":
                messagebox.showwarning("Caja cerrada", "La caja de hoy está cerrada.\n\nSi necesitas reabrir, ingresa como admin y usa REABRIR CAJA.")
                return
            if obtener_apertura_caja(fecha_iso, self.usuario_actual) is not None:
                messagebox.showinfo("Caja", "La caja de hoy ya está abierta para este usuario")
                return
            dialog = ctk.CTkInputDialog(text="Fondo de caja (S/):", title="Apertura de caja")
            monto_txt = dialog.get_input()
            if monto_txt is None:
                return
            try:
                monto_inicial = float(str(monto_txt).strip().replace(",", ".") or "0")
            except ValueError:
                messagebox.showerror("Error", "Fondo de caja inválido")
                return
            if monto_inicial < 0:
                messagebox.showerror("Error", "Fondo de caja inválido")
                return
            ok = registrar_apertura_caja(fecha_iso, datetime.now().strftime("%H:%M:%S"), self.usuario_actual, monto_inicial)
            if not ok:
                messagebox.showwarning("Caja", "Ya existe una caja abierta hoy para este usuario")
                return
            self.mostrar_caja()

        def ingreso_efectivo_ui():
            if caja_cerrada:
                messagebox.showwarning("Caja cerrada", "La caja está cerrada. No se pueden registrar ingresos.")
                return
            apertura_local = obtener_apertura_caja(fecha_iso, self.usuario_actual)
            if apertura_local is None or str(apertura_local[4] or "").upper() != "ABIERTA":
                messagebox.showwarning("Caja", "No hay caja ABIERTA.\n\nAbre caja para registrar ingresos.")
                return
            dialog = ctk.CTkInputDialog(text="Monto de ingreso (S/):", title="Ingreso de efectivo")
            monto_txt = dialog.get_input()
            if monto_txt is None:
                return
            try:
                monto = float(str(monto_txt).strip().replace(",", ".") or "0")
            except ValueError:
                messagebox.showerror("Error", "Monto inválido")
                return
            if monto <= 0:
                messagebox.showerror("Error", "Monto inválido")
                return
            dialog = ctk.CTkInputDialog(text="Descripción (opcional):", title="Ingreso de efectivo")
            desc = dialog.get_input()
            desc = (str(desc).strip() if desc is not None else "")
            registrar_movimiento_caja(fecha_iso, datetime.now().strftime("%H:%M:%S"), self.usuario_actual, "INGRESO", monto, desc or None)
            self.mostrar_caja()

        def egreso_efectivo_ui():
            if caja_cerrada:
                messagebox.showwarning("Caja cerrada", "La caja está cerrada. No se pueden registrar egresos.")
                return
            apertura_local = obtener_apertura_caja(fecha_iso, self.usuario_actual)
            if apertura_local is None or str(apertura_local[4] or "").upper() != "ABIERTA":
                messagebox.showwarning("Caja", "No hay caja ABIERTA.\n\nAbre caja para registrar egresos.")
                return
            dialog = ctk.CTkInputDialog(text="Monto de egreso (S/):", title="Salida de efectivo")
            monto_txt = dialog.get_input()
            if monto_txt is None:
                return
            try:
                monto = float(str(monto_txt).strip().replace(",", ".") or "0")
            except ValueError:
                messagebox.showerror("Error", "Monto inválido")
                return
            if monto <= 0:
                messagebox.showerror("Error", "Monto inválido")
                return
            dialog = ctk.CTkInputDialog(text="Descripción del gasto (obligatoria):", title="Salida de efectivo")
            desc = dialog.get_input()
            if desc is None:
                return
            desc = str(desc).strip()
            if not desc:
                messagebox.showwarning("Descripción requerida", "Debes ingresar una descripción del egreso")
                return
            registrar_movimiento_caja(fecha_iso, datetime.now().strftime("%H:%M:%S"), self.usuario_actual, "EGRESO", monto, desc)
            self.mostrar_caja()

        if caja_cerrada:
            def reabrir_caja_ui():
                if self.rol_actual != "admin":
                    messagebox.showerror("Permiso denegado", "Solo admin puede reabrir caja")
                    return
                cierre_local = obtener_cierre_caja(fecha_iso, self.usuario_actual)
                cierre_estado_local = (str(cierre_local[10]).upper() if (cierre_local is not None and cierre_local[10] is not None) else "CERRADA") if cierre_local is not None else ""
                if cierre_local is None or cierre_estado_local != "CERRADA":
                    messagebox.showinfo("Caja", "La caja no está cerrada")
                    return
                ok = messagebox.askyesno("Reabrir caja", "¿Seguro de REABRIR la caja de hoy?")
                if not ok:
                    return
                dialog = ctk.CTkInputDialog(text="Motivo de reapertura:", title="Reabrir caja")
                motivo = dialog.get_input()
                if motivo is None:
                    return
                motivo = str(motivo).strip()
                reabrir_caja(fecha_iso, self.usuario_actual, self.usuario_actual, motivo)
                self.mostrar_caja()

            btn_abrir = ctk.CTkButton(
                acciones,
                text="🔓 REABRIR CAJA",
                font=ctk.CTkFont(size=16, weight="bold"),
                fg_color="#F1C40F",
                height=50,
                command=reabrir_caja_ui,
            )
            if self.rol_actual != "admin":
                btn_abrir.configure(state="disabled")
        elif apertura_abierta:
            btn_abrir = ctk.CTkButton(
                acciones,
                text="🔓 CAJA ABIERTA",
                font=ctk.CTkFont(size=16, weight="bold"),
                fg_color="#27AE60",
                height=50,
                state="disabled",
            )
        else:
            btn_abrir = ctk.CTkButton(
                acciones,
                text="🔓 ABRIR CAJA",
                font=ctk.CTkFont(size=16, weight="bold"),
                fg_color="#27AE60",
                height=50,
                command=abrir_caja,
            )
        btn_abrir.pack(side="left", padx=(0, 10))

        btn_cerrar = ctk.CTkButton(
            acciones,
            text="📄 CERRAR CAJA (PDF)",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#3498DB",
            height=50,
            command=cerrar_caja_pdf,
        )
        if caja_cerrada:
            btn_cerrar.configure(state="disabled")
        btn_cerrar.pack(side="left")

        btn_ingreso = ctk.CTkButton(
            acciones,
            text="➕ INGRESO",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.color_success,
            height=50,
            command=ingreso_efectivo_ui,
        )
        if caja_cerrada:
            btn_ingreso.configure(state="disabled")
        btn_ingreso.pack(side="left", padx=(10, 0))

        btn_egreso = ctk.CTkButton(
            acciones,
            text="➖ EGRESO",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.color_danger,
            height=50,
            command=egreso_efectivo_ui,
        )
        if caja_cerrada:
            btn_egreso.configure(state="disabled")
        btn_egreso.pack(side="left", padx=(10, 0))

        btn_x = ctk.CTkButton(
            acciones,
            text="📄 REPORTE X (PDF)",
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#9B59B6",
            height=50,
            command=reporte_x_pdf,
        )
        if caja_cerrada:
            btn_x.configure(state="disabled")
        btn_x.pack(side="left", padx=(10, 0))

        resumen_frame = ctk.CTkFrame(container, fg_color="#2C3E50")
        resumen_frame.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(resumen_frame, text="RESUMEN DEL DÍA", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.color_primary).pack(
            pady=(10, 5)
        )
        resumen_metodo_ui = obtener_resumen_por_metodo(fecha_iso, fecha_iso, filtro_usuario_ventas)
        ventas_count_ui = sum(int(c) for _, c, _ in resumen_metodo_ui)
        efectivo_ui = 0.0
        tarjeta_ui = 0.0
        qr_ui = 0.0
        for m, _, t in resumen_metodo_ui:
            mm = str(m or "").strip().lower()
            if mm == "efectivo":
                efectivo_ui += float(t)
            elif mm == "tarjeta":
                tarjeta_ui += float(t)
            elif mm in {"qr", "yape/plin", "yape", "plin", "qr (yape/plin)"}:
                qr_ui += float(t)
        total_ing_ui, total_egr_ui = resumen_movimientos(fecha_iso, fecha_iso, self.usuario_actual)
        apertura_ui = obtener_apertura_caja(fecha_iso, self.usuario_actual)
        fondo_ui = float(apertura_ui[3] or 0) if apertura_ui else 0.0
        efectivo_esp_ui = fondo_ui + efectivo_ui + float(total_ing_ui) - float(total_egr_ui)
        ctk.CTkLabel(resumen_frame, text=f"Ventas: {ventas_count_ui}", font=ctk.CTkFont(size=14)).pack()
        ctk.CTkLabel(
            resumen_frame,
            text=f"Efectivo: S/ {efectivo_ui:.2f}   |   Tarjeta: S/ {tarjeta_ui:.2f}   |   QR: S/ {qr_ui:.2f}",
            font=ctk.CTkFont(size=14),
        ).pack(pady=(2, 2))
        ctk.CTkLabel(
            resumen_frame,
            text=f"Fondo: S/ {fondo_ui:.2f}   |   Ingresos: S/ {float(total_ing_ui):.2f}   |   Egresos: S/ {float(total_egr_ui):.2f}",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        ).pack(pady=(0, 2))
        ctk.CTkLabel(
            resumen_frame,
            text=f"Efectivo esperado: S/ {efectivo_esp_ui:.2f}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="gray",
        ).pack(pady=(0, 8))
        if caja_cerrada:
            _, hora_c, total_c, _, _, t_ef, t_ya, v_cnt, ef_cont, dif_ef, *_rest = cierre
            if ef_cont is not None and dif_ef is not None:
                ctk.CTkLabel(
                    resumen_frame,
                    text=f"Cierre: {hora_c} | Contado: S/ {float(ef_cont):.2f} | Dif: S/ {float(dif_ef):.2f}",
                    font=ctk.CTkFont(size=13),
                    text_color="gray",
                ).pack(pady=(0, 10))
            else:
                ctk.CTkLabel(resumen_frame, text=f"Cierre: {hora_c}", font=ctk.CTkFont(size=13), text_color="gray").pack(pady=(0, 10))
        else:
            ctk.CTkLabel(
                resumen_frame,
                text="Caja abierta: las ventas se acumulan automáticamente",
                font=ctk.CTkFont(size=13),
                text_color="gray",
            ).pack(pady=(0, 10))

        movs_frame = ctk.CTkFrame(container, fg_color="#2C3E50")
        movs_frame.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(movs_frame, text="MOVIMIENTOS", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.color_primary).pack(pady=(10, 8))
        movs_ui = obtener_movimientos_dia(self.usuario_actual)
        if movs_ui:
            for _, _, hora_m, tipo_m, monto_m, desc_m, _u in movs_ui:
                d = (str(desc_m).strip() if desc_m is not None else "")
                if d:
                    txt = f"{hora_m} | {tipo_m} | S/ {float(monto_m):.2f} | {d}"
                else:
                    txt = f"{hora_m} | {tipo_m} | S/ {float(monto_m):.2f}"
                ctk.CTkLabel(movs_frame, text=txt, font=ctk.CTkFont(size=13), anchor="w", justify="left", wraplength=1050).pack(
                    anchor="w", padx=15, pady=3
                )
        else:
            ctk.CTkLabel(movs_frame, text="Sin movimientos", font=ctk.CTkFont(size=13), text_color="gray").pack(pady=(0, 12))

        ventas_frame = ctk.CTkFrame(container, fg_color="#2C3E50")
        ventas_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(ventas_frame, text="VENTAS DEL DÍA", font=ctk.CTkFont(size=20, weight="bold"), text_color=self.color_primary).pack(pady=15)

        header_cols = ctk.CTkFrame(ventas_frame, fg_color="#22303C")
        header_cols.pack(fill="x", padx=10, pady=(0, 8))
        header_cols.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header_cols, text="HORA", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray").grid(row=0, column=0, padx=12, pady=8, sticky="w")
        ctk.CTkLabel(header_cols, text="DETALLE", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray").grid(row=0, column=1, padx=12, pady=8, sticky="w")
        ctk.CTkLabel(header_cols, text="TOTAL", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray").grid(row=0, column=2, padx=12, pady=8, sticky="e")

        def _reimprimir_ticket_venta(fecha_local, venta_id, hora, items_txt, total_v, usuario, metodo, cliente=None):
            ticket_num = f"T-{int(venta_id):04d}"
            lineas = []
            lineas.append(f"Fecha: {fecha_local} {hora}")
            lineas.append(f"Ticket: {ticket_num}")
            c = str(cliente or "").strip()
            if c:
                lineas.append(f"Cliente: {c}")
            lineas.append(f"Usuario: {usuario}")
            lineas.append(f"Método: {metodo}")
            lineas.append("")
            lineas.append("Detalle:")
            parts = [p.strip() for p in str(items_txt or "").split(",") if str(p or "").strip()]
            if parts:
                for p in parts:
                    lineas.append(f"- {p}")
            else:
                lineas.append("- (Sin detalle)")
            lineas.append("")
            lineas.append(f"TOTAL: S/ {float(total_v):.2f}")
            try:
                imprimir_ticket_texto("TICKET DE COMPRA", lineas, subtitulo=APP_NAME, printer_name=self._printer_name())
            except Exception as e:
                messagebox.showerror("Impresión", f"No se pudo reimprimir el ticket.\n\n{e}")

        ventas = obtener_ventas_dia(filtro_usuario_ventas, incluir_anuladas=(self.rol_actual == "admin"))
        for venta in ventas:
            if len(venta) >= 9:
                venta_id, hora, items, total_v, metodo, usuario, anulada, motivo, cliente = venta[:9]
            else:
                venta_id, hora, items, total_v, metodo, usuario, anulada, motivo = venta
                cliente = None

            venta_frame = ctk.CTkFrame(ventas_frame, fg_color="#34495E", corner_radius=12)
            venta_frame.pack(fill="x", padx=10, pady=6)
            venta_frame.grid_columnconfigure(1, weight=1)

            hora_txt = f"🕐 {hora}"
            if anulada:
                hora_txt += "  (ANULADA)"
            ctk.CTkLabel(venta_frame, text=hora_txt, font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=12, pady=12, sticky="w")

            detalle = items
            c = str(cliente or "").strip()
            if c:
                detalle = f"{detalle}\nCliente: {c}"
            if self.rol_actual == "admin":
                detalle = f"{items}  |  {usuario}  |  {metodo}"
                if c:
                    detalle = f"{detalle}\nCliente: {c}"
            if anulada and motivo:
                detalle = f"{detalle}\nMotivo: {motivo}"
            detalle_color = "gray" if anulada else "white"
            ctk.CTkLabel(
                venta_frame,
                text=detalle,
                font=ctk.CTkFont(size=14),
                anchor="w",
                justify="left",
                text_color=detalle_color,
                wraplength=760,
            ).grid(row=0, column=1, padx=12, pady=12, sticky="nsew")

            total_color = "gray" if anulada else self.color_success
            ctk.CTkLabel(
                venta_frame,
                text=f"S/ {total_v:.2f}",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=total_color,
            ).grid(row=0, column=2, padx=12, pady=12, sticky="e")

            btns_frame = ctk.CTkFrame(venta_frame, fg_color="transparent")
            btns_frame.grid(row=0, column=3, padx=(0, 12), pady=10, sticky="e")
            btn_print = ctk.CTkButton(
                btns_frame,
                text="🖨️",
                width=45,
                height=40,
                fg_color="#3498DB",
                command=lambda vid=venta_id, h=hora, it=items, tv=total_v, u=usuario, m=metodo, c=cliente: _reimprimir_ticket_venta(
                    fecha_iso, vid, h, it, tv, u, m, c
                ),
            )
            if anulada:
                btn_print.configure(state="disabled")
            btn_print.pack(side="left", padx=(0, 8))

            if self.rol_actual == "admin" and not anulada:
                def anular(vid=venta_id):
                    ok = messagebox.askyesno("Confirmar", "¿Seguro de anular esta venta?")
                    if not ok:
                        return
                    dialog = ctk.CTkInputDialog(text="Motivo de anulación:", title="Anular Venta")
                    motivo_local = dialog.get_input()
                    if motivo_local is None:
                        return
                    motivo_local = str(motivo_local).strip()
                    if not motivo_local:
                        messagebox.showwarning("Motivo requerido", "Debes ingresar un motivo para anular")
                        return
                    anular_venta(vid, motivo_local, self.usuario_actual)
                    self.mostrar_caja()

                ctk.CTkButton(btns_frame, text="ANULAR", width=90, height=40, fg_color=self.color_danger, command=anular).pack(
                    side="left"
                )

    def mostrar_reportes(self):
        self.clear_window()

        header = ctk.CTkFrame(self, height=80, fg_color=self.color_secondary)
        header.pack(fill="x")

        ctk.CTkLabel(header, text="📊 REPORTES", font=ctk.CTkFont(size=28, weight="bold"), text_color=self.color_primary).pack(side="left", padx=20)

        ctk.CTkButton(
            header,
            text="← VOLVER",
            font=ctk.CTkFont(size=16),
            fg_color=self.color_danger,
            width=150,
            height=50,
            command=self.mostrar_dashboard,
        ).pack(side="right", padx=20)

        container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        stats_container = ctk.CTkFrame(container, fg_color="transparent")
        stats_container.pack(fill="x", pady=(0, 20))

        hoy = datetime.now().date()
        fecha_fin = hoy.strftime("%Y-%m-%d")
        fecha_inicio_sem = (hoy - timedelta(days=6)).strftime("%Y-%m-%d")
        fecha_inicio_mes = hoy.replace(day=1).strftime("%Y-%m-%d")

        filtro_usuario = None if self.rol_actual == "admin" else self.usuario_actual

        fecha_diaria_var = StringVar(value=fecha_fin)

        def _norm_metodo_rep(metodo):
            s = str(metodo or "").strip().lower()
            if s == "efectivo":
                return "Efectivo"
            if s == "tarjeta":
                return "Tarjeta"
            if s in {"qr", "yape/plin", "yape", "plin", "qr (yape/plin)"}:
                return "QR"
            return str(metodo or "Sin método")

        def _validar_fecha_iso(fecha_txt):
            try:
                datetime.strptime(str(fecha_txt).strip(), "%Y-%m-%d")
                return True
            except Exception:
                return False

        resumen_sem = obtener_resumen_por_dia(fecha_inicio_sem, fecha_fin, filtro_usuario)
        resumen_mes = obtener_resumen_por_dia(fecha_inicio_mes, fecha_fin, filtro_usuario)
        total_sem = sum(t for _, _, t in resumen_sem)
        total_mes = sum(t for _, _, t in resumen_mes)

        stats_container.grid_columnconfigure(0, weight=1)
        stats_container.grid_columnconfigure(1, weight=1)

        card_dia = ctk.CTkFrame(stats_container, fg_color="#2C3E50", corner_radius=15)
        card_dia.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        card_sem = ctk.CTkFrame(stats_container, fg_color="#2C3E50", corner_radius=15)
        card_sem.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        card_mes = ctk.CTkFrame(stats_container, fg_color="#2C3E50", corner_radius=15)
        card_mes.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(card_dia, text="REPORTE DIARIO", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.color_primary).pack(pady=(15, 5))
        label_dia_fecha = ctk.CTkLabel(card_dia, text=fecha_diaria_var.get(), font=ctk.CTkFont(size=12), text_color="gray")
        label_dia_fecha.pack()
        label_dia_total = ctk.CTkLabel(card_dia, text="S/ 0.00", font=ctk.CTkFont(size=34, weight="bold"), text_color=self.color_success)
        label_dia_total.pack(pady=(10, 0))
        label_dia_count = ctk.CTkLabel(card_dia, text="0 ventas", font=ctk.CTkFont(size=12), text_color="gray")
        label_dia_count.pack(pady=(0, 6))
        label_dia_metodos = ctk.CTkLabel(card_dia, text="-", font=ctk.CTkFont(size=12), justify="left")
        label_dia_metodos.pack(pady=(0, 10))

        ctk.CTkLabel(card_sem, text="REPORTE SEMANAL", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.color_primary).pack(pady=(15, 5))
        ctk.CTkLabel(card_sem, text=f"{fecha_inicio_sem} a {fecha_fin}", font=ctk.CTkFont(size=12), text_color="gray").pack()
        ctk.CTkLabel(card_sem, text=f"S/ {total_sem:.2f}", font=ctk.CTkFont(size=34, weight="bold"), text_color=self.color_success).pack(pady=10)

        ctk.CTkLabel(card_mes, text="REPORTE MENSUAL", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.color_primary).pack(pady=(15, 5))
        ctk.CTkLabel(card_mes, text=f"{fecha_inicio_mes} a {fecha_fin}", font=ctk.CTkFont(size=12), text_color="gray").pack()
        ctk.CTkLabel(card_mes, text=f"S/ {total_mes:.2f}", font=ctk.CTkFont(size=34, weight="bold"), text_color=self.color_success).pack(pady=10)

        detalle_diario = ctk.CTkFrame(container, fg_color="#2C3E50", corner_radius=15)
        detalle_diario.pack(fill="x", padx=10, pady=(0, 20))
        detalle_diario.grid_columnconfigure(0, weight=1)
        detalle_diario.grid_columnconfigure(1, weight=2)

        ctk.CTkLabel(detalle_diario, text="DETALLE DIARIO", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.color_primary).grid(
            row=0, column=0, columnspan=2, padx=15, pady=(12, 8), sticky="w"
        )

        resumen_frame = ctk.CTkFrame(detalle_diario, fg_color="transparent")
        resumen_frame.grid(row=1, column=0, padx=15, pady=(0, 12), sticky="nsew")

        ventas_frame = ctk.CTkFrame(detalle_diario, fg_color="transparent")
        ventas_frame.grid(row=1, column=1, padx=15, pady=(0, 12), sticky="nsew")

        resumen_txt = ctk.CTkLabel(resumen_frame, text="", justify="left")
        resumen_txt.pack(anchor="w")

        def _render_ventas_diarias(ventas_local):
            for w in ventas_frame.winfo_children():
                w.destroy()
            if not ventas_local:
                ctk.CTkLabel(ventas_frame, text="Sin ventas").pack(anchor="w", padx=5, pady=5)
                return
            fecha_local = str(fecha_diaria_var.get()).strip()
            for venta_id, _f, hora, items, total_v, usuario, metodo, anulada, _motivo in ventas_local:
                if self.rol_actual == "admin":
                    txt = f"{hora} | T-{int(venta_id):04d} | {_norm_metodo_rep(metodo)} | {usuario} | S/ {float(total_v):.2f} | {items}"
                else:
                    txt = f"{hora} | T-{int(venta_id):04d} | {_norm_metodo_rep(metodo)} | S/ {float(total_v):.2f} | {items}"

                row = ctk.CTkFrame(ventas_frame, fg_color="transparent")
                row.pack(fill="x", padx=5, pady=4)

                ctk.CTkLabel(row, text=txt, justify="left", wraplength=560).pack(side="left", fill="x", expand=True)

                def _reimprimir_rep(vid=venta_id, h=hora, it=items, tv=total_v, u=usuario, m=metodo):
                    ticket_num = f"T-{int(vid):04d}"
                    lineas = []
                    lineas.append(f"Fecha: {fecha_local} {h}")
                    lineas.append(f"Ticket: {ticket_num}")
                    lineas.append(f"Usuario: {u}")
                    lineas.append(f"Método: {m}")
                    lineas.append("")
                    lineas.append("Detalle:")
                    parts = [p.strip() for p in str(it or "").split(",") if str(p or "").strip()]
                    if parts:
                        for p in parts:
                            lineas.append(f"- {p}")
                    else:
                        lineas.append("- (Sin detalle)")
                    lineas.append("")
                    lineas.append(f"TOTAL: S/ {float(tv):.2f}")
                    try:
                        imprimir_ticket_texto("TICKET DE COMPRA", lineas, subtitulo=APP_NAME, printer_name=self._printer_name())
                    except Exception as e:
                        messagebox.showerror("Impresión", f"No se pudo reimprimir el ticket.\n\n{e}")

                btn = ctk.CTkButton(row, text="🖨️", width=45, height=32, fg_color="#3498DB", command=_reimprimir_rep)
                if anulada:
                    btn.configure(state="disabled")
                btn.pack(side="right", padx=(8, 0))

        def _refrescar_diario():
            fecha_local = str(fecha_diaria_var.get()).strip()
            if not _validar_fecha_iso(fecha_local):
                return

            label_dia_fecha.configure(text=fecha_local)

            resumen_dia = obtener_resumen_por_dia(fecha_local, fecha_local, filtro_usuario)
            if resumen_dia:
                _f, cant, total = resumen_dia[0]
            else:
                cant, total = 0, 0.0
            label_dia_total.configure(text=f"S/ {float(total):.2f}")
            label_dia_count.configure(text=f"{int(cant)} ventas")

            resumen_metodo = obtener_resumen_por_metodo(fecha_local, fecha_local, filtro_usuario)
            if resumen_metodo:
                metodos = {}
                for metodo, c, t in resumen_metodo:
                    k = _norm_metodo_rep(metodo)
                    if k not in metodos:
                        metodos[k] = [0, 0.0]
                    metodos[k][0] += int(c or 0)
                    metodos[k][1] += float(t or 0)
                lines = []
                for k in ["Efectivo", "Tarjeta", "QR"]:
                    if k in metodos:
                        c, t = metodos[k]
                        lines.append(f"{k}: {c} | S/ {t:.2f}")
                for k in sorted([kk for kk in metodos.keys() if kk not in {"Efectivo", "Tarjeta", "QR"}]):
                    c, t = metodos[k]
                    lines.append(f"{k}: {c} | S/ {t:.2f}")
                label_dia_metodos.configure(text="\n".join(lines) if lines else "-")
                resumen_txt.configure(text="\n".join(lines) if lines else "-")
            else:
                label_dia_metodos.configure(text="-")
                resumen_txt.configure(text="-")

            ventas_local = obtener_ventas_rango(fecha_local, fecha_local, filtro_usuario)
            _render_ventas_diarias(ventas_local)

        def _cambiar_fecha_diaria():
            dialog = ctk.CTkInputDialog(text="Fecha (YYYY-MM-DD):", title="Reporte diario")
            fecha_txt = dialog.get_input()
            if fecha_txt is None:
                return
            fecha_txt = str(fecha_txt).strip()
            if not _validar_fecha_iso(fecha_txt):
                messagebox.showerror("Error", "Fecha inválida. Usa formato YYYY-MM-DD")
                return
            fecha_diaria_var.set(fecha_txt)
            _refrescar_diario()

        def _pdf_diario():
            fecha_local = str(fecha_diaria_var.get()).strip()
            if not _validar_fecha_iso(fecha_local):
                messagebox.showerror("Error", "Fecha inválida. Usa formato YYYY-MM-DD")
                return

            sugerido = f"reporte_diario_{fecha_local}.pdf".replace("-", "")
            file_path = filedialog.asksaveasfilename(
                title="Guardar reporte diario (PDF)",
                defaultextension=".pdf",
                initialfile=sugerido,
                filetypes=[("PDF", "*.pdf")],
            )
            if not file_path:
                return

            resumen_dia = obtener_resumen_por_dia(fecha_local, fecha_local, filtro_usuario)
            if resumen_dia:
                _f, cant, total = resumen_dia[0]
            else:
                cant, total = 0, 0.0
            resumen_metodo = obtener_resumen_por_metodo(fecha_local, fecha_local, filtro_usuario)
            ventas_local = obtener_ventas_rango(fecha_local, fecha_local, filtro_usuario)

            lineas = []
            lineas.append(f"Fecha: {fecha_local}")
            if filtro_usuario:
                lineas.append(f"Usuario: {filtro_usuario}")
            else:
                lineas.append("Usuario: Todos")
            lineas.append("")
            lineas.append(f"TOTAL: {int(cant)} ventas | S/ {float(total):.2f}")
            lineas.append("")
            lineas.append("Resumen por método de pago:")
            if resumen_metodo:
                metodos = {}
                for metodo, c, t in resumen_metodo:
                    k = _norm_metodo_rep(metodo)
                    if k not in metodos:
                        metodos[k] = [0, 0.0]
                    metodos[k][0] += int(c or 0)
                    metodos[k][1] += float(t or 0)
                for k in ["Efectivo", "Tarjeta", "QR"]:
                    if k in metodos:
                        c, t = metodos[k]
                        lineas.append(f"- {k}: {c} ventas | S/ {t:.2f}")
                for k in sorted([kk for kk in metodos.keys() if kk not in {"Efectivo", "Tarjeta", "QR"}]):
                    c, t = metodos[k]
                    lineas.append(f"- {k}: {c} ventas | S/ {t:.2f}")
            else:
                lineas.append("- Sin datos")

            lineas.append("")
            if len(ventas_local) <= 60:
                lineas.append("Ventas del día:")
                for venta_id, _f, hora, items, total_v, usuario, metodo, _anulada, _motivo in ventas_local:
                    if self.rol_actual == "admin":
                        lineas.append(f"{hora} | T-{int(venta_id):04d} | {_norm_metodo_rep(metodo)} | {usuario} | S/ {float(total_v):.2f} | {items}")
                    else:
                        lineas.append(f"{hora} | T-{int(venta_id):04d} | {_norm_metodo_rep(metodo)} | S/ {float(total_v):.2f} | {items}")
            else:
                lineas.append("Ventas del día:")
                lineas.append(f"- Detalle omitido (tickets: {len(ventas_local)})")

            try:
                generar_pdf_ticket(file_path, "REPORTE DIARIO", lineas)
                messagebox.showinfo("Reporte diario", f"PDF generado:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}")

        botones_dia = ctk.CTkFrame(card_dia, fg_color="transparent")
        botones_dia.pack(pady=(0, 15))
        ctk.CTkButton(botones_dia, text="📅 FECHA", fg_color="#3498DB", width=140, height=45, command=_cambiar_fecha_diaria).pack(side="left", padx=8)
        ctk.CTkButton(botones_dia, text="📄 PDF", fg_color="#3498DB", width=140, height=45, command=_pdf_diario).pack(side="left", padx=8)

        def exportar_pdf_rango(nombre, fecha_inicio, fecha_fin):
            sugerido = f"reporte_{nombre}_{fecha_inicio}_a_{fecha_fin}.pdf".replace("-", "")
            file_path = filedialog.asksaveasfilename(
                title="Guardar reporte (PDF)",
                defaultextension=".pdf",
                initialfile=sugerido,
                filetypes=[("PDF", "*.pdf")],
            )
            if not file_path:
                return

            resumen_dia = obtener_resumen_por_dia(fecha_inicio, fecha_fin, filtro_usuario)
            resumen_metodo = obtener_resumen_por_metodo(fecha_inicio, fecha_fin, filtro_usuario)
            total_r = sum(t for _, _, t in resumen_dia)
            cant = sum(c for _, c, _ in resumen_dia)

            lineas = []
            lineas.append(f"Rango: {fecha_inicio} a {fecha_fin}")
            lineas.append("")
            lineas.append("Resumen por día:")
            if resumen_dia:
                for f, c, t in resumen_dia:
                    lineas.append(f"- {f}: {c} ventas | S/ {t:.2f}")
            else:
                lineas.append("- Sin ventas en el rango")
            lineas.append("")
            lineas.append("Resumen por método de pago:")
            if resumen_metodo:
                metodos = {}
                for metodo, c, t in resumen_metodo:
                    k = _norm_metodo_rep(metodo)
                    if k not in metodos:
                        metodos[k] = [0, 0.0]
                    metodos[k][0] += int(c or 0)
                    metodos[k][1] += float(t or 0)

                for k in ["Efectivo", "Tarjeta", "QR"]:
                    if k in metodos:
                        c, t = metodos[k]
                        lineas.append(f"- {k}: {c} ventas | S/ {t:.2f}")
                for k in sorted([kk for kk in metodos.keys() if kk not in {"Efectivo", "Tarjeta", "QR"}]):
                    c, t = metodos[k]
                    lineas.append(f"- {k}: {c} ventas | S/ {t:.2f}")
            else:
                lineas.append("- Sin datos")
            lineas.append("")
            lineas.append(f"TOTAL: {cant} ventas | S/ {total_r:.2f}")

            try:
                generar_pdf_ticket(file_path, f"REPORTE {nombre.upper()}", lineas)
                messagebox.showinfo("Reporte", f"PDF generado:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}")

        ctk.CTkButton(
            card_sem,
            text="📄 PDF",
            fg_color="#3498DB",
            width=140,
            height=45,
            command=lambda: exportar_pdf_rango("semanal", fecha_inicio_sem, fecha_fin),
        ).pack(pady=(0, 15))
        ctk.CTkButton(
            card_mes,
            text="📄 PDF",
            fg_color="#3498DB",
            width=140,
            height=45,
            command=lambda: exportar_pdf_rango("mensual", fecha_inicio_mes, fecha_fin),
        ).pack(pady=(0, 15))

        _refrescar_diario()

        listas = ctk.CTkFrame(container, fg_color="transparent")
        listas.pack(fill="x")
        listas.grid_columnconfigure(0, weight=1)
        listas.grid_columnconfigure(1, weight=1)

        sem_frame = ctk.CTkFrame(listas, fg_color="#2C3E50")
        sem_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(sem_frame, text="DETALLE SEMANAL", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.color_primary).pack(pady=10)
        for f, c, t in resumen_sem:
            ctk.CTkLabel(sem_frame, text=f"{f}  |  {c} ventas  |  S/ {t:.2f}", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=15, pady=6)

        mes_frame = ctk.CTkFrame(listas, fg_color="#2C3E50")
        mes_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(mes_frame, text="DETALLE MENSUAL", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.color_primary).pack(pady=10)
        for f, c, t in resumen_mes:
            ctk.CTkLabel(mes_frame, text=f"{f}  |  {c} ventas  |  S/ {t:.2f}", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=15, pady=6)
