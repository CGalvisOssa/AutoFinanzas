"""
Sistema de Ventas - CustomTkinter + MySQL (XAMPP)
Requiere: pip install customtkinter mysql-connector-python requests
"""

import customtkinter as ctk
import mysql.connector
import requests
import json
import hashlib
from datetime import datetime
from tkinter import messagebox, ttk
import tkinter as tk

# ── Configuración ─────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "",
    "database": "ventas_db"
}

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Paleta industrial cálida
ACCENT  = "#c0392b"      # rojo ladrillo
ACCENT2 = "#2c3e50"      # azul petróleo
DANGER  = "#e74c3c"
BG      = "#f5f0eb"      # crema cálido
SURFACE = "#ffffff"
BORDER  = "#d5cdc4"
MUTED   = "#8b7d6b"
TEXT    = "#2c2416"
HEADER  = "#2c3e50"

# ── Base de datos ─────────────────────────────────────────────
def conectar():
    return mysql.connector.connect(**DB_CONFIG)

def query(sql, params=None, fetch=True):
    conn = conectar()
    cur  = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    if fetch:
        rows = cur.fetchall()
        conn.close()
        return rows
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

# ── Helpers ───────────────────────────────────────────────────
def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()

def fmt_money(val):
    try:    return f"${float(val):,.0f}"
    except: return "$0"

def toast(msg, color=ACCENT):
    win = ctk.CTkToplevel()
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.configure(fg_color=SURFACE)
    ctk.CTkLabel(win, text=msg, text_color=color,
                  font=ctk.CTkFont("Helvetica", 12)).pack(padx=20, pady=14)
    # posicionar abajo a la derecha
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    w  = win.winfo_width()
    h  = win.winfo_height()
    win.geometry(f"+{sw-w-40}+{sh-h-80}")
    win.after(2500, win.destroy)

# ══════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self, usuario=None):
        super().__init__()
        self._reiniciar = False
        self.usuario = usuario or {"id": 1, "nombre": "Admin", "rol": "administrador"}
        self.title(f"PaperPoint Ventas  —  {self.usuario['nombre']}  ({self.usuario['rol']})")
        self.geometry("1100x700")
        self.configure(fg_color=BG)
        self.resizable(True, True)

        self._build_nav()
        self._build_content()
        self.mostrar_tab("esp32")

    # ── Navegación ────────────────────────────────────────────
    def _build_nav(self):
        nav = ctk.CTkFrame(self, fg_color=HEADER, corner_radius=0, height=52)
        nav.pack(fill="x", side="top")
        nav.pack_propagate(False)

        ctk.CTkLabel(nav, text="◈  PaperPoint Ventas",
                     font=ctk.CTkFont("Georgia", 13, "bold"),
                     text_color=SURFACE).pack(side="left", padx=20)
        # Ocultar tab usuarios si no es admin (se configura en mostrar_tab)
        ctk.CTkButton(nav, text="Cerrar sesión", width=120, height=30,
                      fg_color="#a93226", hover_color="#922b21",
                      text_color="#ffffff", corner_radius=4,
                      font=ctk.CTkFont("Helvetica", 11),
                      command=self._cerrar_sesion).pack(side="right", padx=16)

        self.nav_btns = {}
        tabs = [("esp32","ESP32"), ("productos","Productos"), ("clientes","Clientes"),
                ("ventas","Ventas"), ("estadisticas","Estadísticas"), ("usuarios","Usuarios")]
        for key, label in tabs:
            b = ctk.CTkButton(nav, text=label, width=110, height=34,
                              fg_color="transparent", text_color="#b0c4d8",
                              hover_color="#3d5166", corner_radius=4,
                              font=ctk.CTkFont("Helvetica", 12),
                              command=lambda k=key: self.mostrar_tab(k))
            b.pack(side="left", padx=1)
            self.nav_btns[key] = b

    def _build_content(self):
        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.pack(fill="both", expand=True)
        self.frames = {}
        for name, cls in [("esp32", TabESP32), ("productos", TabProductos),
                          ("clientes", TabClientes), ("ventas", TabVentas),
                          ("estadisticas", TabEstadisticas), ("usuarios", TabUsuarios)]:
            f = cls(self.content, self)
            f.place(relwidth=1, relheight=1)
            self.frames[name] = f

    def _cerrar_sesion(self):
        if messagebox.askyesno("Cerrar sesión", "¿Deseas cerrar sesión?"):
            self._reiniciar = True
            self.destroy()

    def mostrar_tab(self, name):
        # Restringir tab usuarios a solo admins
        if name == "usuarios" and self.usuario.get("rol") != "administrador":
            toast("Solo administradores pueden ver usuarios", DANGER)
            return
        for k, b in self.nav_btns.items():
            b.configure(text_color="#ffffff" if k == name else "#b0c4d8",
                        fg_color=("#c0392b" if k == name else "transparent"))
        self.frames[name].tkraise()
        self.frames[name].on_show()

# ══════════════════════════════════════════════════════════════
#  COMPONENTES COMUNES
# ══════════════════════════════════════════════════════════════
def make_table(parent, cols, col_widths=None):
    """Crea un Treeview estilizado."""
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.Treeview",
                    background=SURFACE, foreground="#2c2416",
                    fieldbackground=SURFACE, borderwidth=0,
                    rowheight=34, font=("Helvetica", 12))
    style.configure("Dark.Treeview.Heading",
                    background="#e8e0d8", foreground="#2c3e50",
                    font=("Helvetica", 10, "bold"), relief="flat")
    style.map("Dark.Treeview", background=[("selected","#f0e8e0")])

    frame = ctk.CTkFrame(parent, fg_color="#faf7f4", corner_radius=5, border_width=1, border_color=BORDER)
    sb = ctk.CTkScrollbar(frame, button_color=BORDER, button_hover_color=MUTED)
    tv = ttk.Treeview(frame, columns=cols, show="headings",
                      style="Dark.Treeview", yscrollcommand=sb.set)
    sb.configure(command=tv.yview)

    for i, col in enumerate(cols):
        w = (col_widths[i] if col_widths else 140)
        tv.heading(col, text=col.upper())
        tv.column(col, width=w, anchor="w")

    tv.pack(side="left", fill="both", expand=True, padx=8, pady=8)
    sb.pack(side="right", fill="y", pady=8)
    return frame, tv

def campo(parent, label, row, col=0, placeholder="", width=180, show=None):
    ctk.CTkLabel(parent, text=label, text_color=MUTED,
                 font=ctk.CTkFont("Helvetica", 10)).grid(
        row=row*2, column=col, sticky="w", padx=(0,12), pady=(8,2))
    e = ctk.CTkEntry(parent, width=width, placeholder_text=placeholder,
                     fg_color="#faf7f4", border_color=BORDER, text_color=TEXT,
                     show=show or "")
    e.grid(row=row*2+1, column=col, sticky="ew", padx=(0,12))
    return e

def btn(parent, text, color=None, command=None, **kw):
    fg = color or ACCENT
    if "text_color" not in kw:
        if fg in (ACCENT, DANGER):
            kw["text_color"] = "#ffffff"
        elif fg == ACCENT2:
            kw["text_color"] = "#ffffff"
        else:
            kw["text_color"] = TEXT
    hover = _darken(fg)
    return ctk.CTkButton(parent, text=text, fg_color=fg,
                         hover_color=hover, font=ctk.CTkFont("Helvetica", 12, "bold"),
                         corner_radius=5, command=command, **kw)

def _darken(hex_color):
    """Oscurece un color hex un 15%"""
    hex_color = hex_color.lstrip("#")
    r,g,b = int(hex_color[0:2],16), int(hex_color[2:4],16), int(hex_color[4:6],16)
    r,g,b = max(0,int(r*0.85)), max(0,int(g*0.85)), max(0,int(b*0.85))
    return f"#{r:02x}{g:02x}{b:02x}"

# ══════════════════════════════════════════════════════════════
#  TAB ESP32
# ══════════════════════════════════════════════════════════════
class TabESP32(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.app = app
        self.reporte = None
        self._build()

    def _build(self):
        pad = {"padx": 32, "pady": 16}

        # Título
        ctk.CTkLabel(self, text="CONEXIÓN ESP32",
                     font=ctk.CTkFont("Georgia", 11, "bold"),
                     text_color=HEADER).pack(anchor="w", **pad)

        # Card IP
        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=6, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=32, pady=(0,12))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=16)

        ctk.CTkLabel(row, text="IP del ESP32:", text_color=MUTED,
                     font=ctk.CTkFont("Courier New", 11)).pack(side="left")
        self.ip_entry = ctk.CTkEntry(row, width=180, fg_color="#faf7f4",
                                      border_color=BORDER, text_color=TEXT,
                                      font=ctk.CTkFont("Courier New", 12))
        self.ip_entry.insert(0, "192.168.0.107")
        self.ip_entry.pack(side="left", padx=12)

        btn(row, "Guardar IP", color=BORDER, command=self.guardar_ip,
            text_color=TEXT, width=110).pack(side="left", padx=4)
        btn(row, "⬇  Obtener reporte", color=ACCENT2,
            command=self.obtener_reporte, width=180).pack(side="left", padx=4)
        self.btn_guardar = btn(row, "✚  Añadir a ventas",
                                command=self.guardar_reporte, width=180)
        self.btn_guardar.pack(side="left", padx=4)
        self.btn_guardar.configure(state="disabled")

        # Salida JSON
        ctk.CTkLabel(self, text="REPORTE DEL DISPOSITIVO",
                     font=ctk.CTkFont("Helvetica", 10),
                     text_color=MUTED).pack(anchor="w", padx=32)
        self.output = ctk.CTkTextbox(self, fg_color="#faf7f4", text_color="#5a4a3a",
                                      font=ctk.CTkFont("Courier New", 11),
                                      border_color=BORDER, corner_radius=10)
        self.output.pack(fill="both", expand=True, padx=32, pady=(4,32))
        self.output.insert("0.0", "Sin reporte cargado.")
        self.output.configure(state="disabled")

    def on_show(self): pass

    def guardar_ip(self):
        toast("IP guardada: " + self.ip_entry.get())

    def obtener_reporte(self):
        ip  = self.ip_entry.get().strip()
        url = f"http://{ip}/reporte"
        self._log("Consultando ESP32...")
        try:
            r = requests.get(url, timeout=5)
            self.reporte = r.json()
            self._log(json.dumps(self.reporte, indent=2, ensure_ascii=False))
            self.btn_guardar.configure(state="normal")
            toast(f"Reporte obtenido: {self.reporte.get('total_ventas',0)} ventas")
        except Exception as e:
            self._log(f"✗ Error: {e}")
            toast("No se pudo conectar al ESP32", DANGER)

    def guardar_reporte(self):
        if not self.reporte:
            toast("Primero obtén el reporte", DANGER)
            return
        ventas = self.reporte.get("ventas", [])
        if not ventas:
            toast("No hay ventas en el reporte")
            return

        insertadas, errores = 0, []
        for item in ventas:
            codigo   = item.get("codigo", "")
            cantidad = int(item.get("cantidad", 1))
            rows = query("SELECT id, precio_unitario FROM productos WHERE codigo=%s", (codigo,))
            if not rows:
                errores.append(f"Código {codigo} no encontrado")
                continue
            prod     = rows[0]
            precio   = float(prod["precio_unitario"])
            subtotal = precio * cantidad
            vid = query(
                "INSERT INTO ventas (cliente_id, usuario_id, fuente, total) VALUES (NULL,1,'esp32',%s)",
                (subtotal,), fetch=False)
            query(
                "INSERT INTO detalle_ventas (venta_id,producto_id,cantidad,precio_unitario,subtotal) VALUES (%s,%s,%s,%s,%s)",
                (vid, prod["id"], cantidad, precio, subtotal), fetch=False)
            insertadas += 1

        msg = f"✔ {insertadas} ventas guardadas"
        if errores: msg += f"\n⚠ {len(errores)} errores"
        self._log(msg + ("\n" + "\n".join(errores) if errores else ""))
        toast(msg)
        self.btn_guardar.configure(state="disabled")
        self.reporte = None

    def _log(self, text):
        self.output.configure(state="normal")
        self.output.delete("0.0", "end")
        self.output.insert("0.0", text)
        self.output.configure(state="disabled")

# ══════════════════════════════════════════════════════════════
#  TAB PRODUCTOS
# ══════════════════════════════════════════════════════════════
class TabProductos(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        # Formulario
        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=6, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=32, pady=20)

        ctk.CTkLabel(card, text="AGREGAR PRODUCTO",
                     font=ctk.CTkFont("Georgia", 11, "bold"),
                     text_color=HEADER).pack(anchor="w", padx=20, pady=(16,4))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=20, pady=(0,16))
        form.columnconfigure((0,1,2,3), weight=1)

        self.e_codigo = campo(form, "CÓDIGO", 0, 0, "01")
        self.e_nombre = campo(form, "NOMBRE", 0, 1, "Lapicero")
        self.e_precio = campo(form, "PRECIO", 0, 2, "800")
        btn(form, "+ Agregar", command=self.agregar).grid(
            row=1, column=3, sticky="s", padx=(0,12), pady=(18,0))

        # Tabla
        tframe, self.tv = make_table(self, ["ID","Código","Nombre","Precio"],
                                      [60, 80, 300, 150])
        tframe.pack(fill="both", expand=True, padx=32, pady=(0,16))

        btn(self, "↻  Actualizar", color=BORDER, text_color=TEXT,
            command=self.cargar, width=140).pack(anchor="e", padx=32, pady=(0,20))

    def on_show(self): self.cargar()

    def cargar(self):
        rows = query("SELECT id,codigo,nombre,precio_unitario FROM productos WHERE activo=1 ORDER BY id")
        self.tv.delete(*self.tv.get_children())
        for r in rows:
            self.tv.insert("", "end", values=(r["id"], r["codigo"], r["nombre"], fmt_money(r["precio_unitario"])))

    def agregar(self):
        c = self.e_codigo.get().strip()
        n = self.e_nombre.get().strip()
        p = self.e_precio.get().strip()
        if not c or not n:
            toast("Completa código y nombre", DANGER); return
        try:
            query("INSERT INTO productos (codigo,nombre,precio_unitario) VALUES (%s,%s,%s)",
                  (c, n, float(p or 0)), fetch=False)
            toast("Producto agregado")
            self.cargar()
            self.e_codigo.delete(0,"end")
            self.e_nombre.delete(0,"end")
            self.e_precio.delete(0,"end")
        except Exception as e:
            toast(str(e), DANGER)

# ══════════════════════════════════════════════════════════════
#  TAB CLIENTES
# ══════════════════════════════════════════════════════════════
class TabClientes(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=6, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=32, pady=20)

        ctk.CTkLabel(card, text="AGREGAR CLIENTE",
                     font=ctk.CTkFont("Georgia", 11, "bold"),
                     text_color=HEADER).pack(anchor="w", padx=20, pady=(16,4))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=20, pady=(0,16))
        form.columnconfigure((0,1,2,3,4), weight=1)

        self.e_nombre = campo(form, "NOMBRE",    0, 0, "Juan Pérez")
        self.e_cedula = campo(form, "CÉDULA",    0, 1, "1004755025")
        self.e_tel    = campo(form, "TELÉFONO",  0, 2, "3001234567")
        self.e_dir    = campo(form, "DIRECCIÓN", 0, 3, "Cll 17 #26")
        btn(form, "+ Agregar", command=self.agregar).grid(
            row=1, column=4, sticky="s", padx=(0,12), pady=(18,0))

        tframe, self.tv = make_table(self,
            ["ID","Nombre","Cédula","Teléfono","Dirección"],
            [50, 200, 140, 130, 260])
        tframe.pack(fill="both", expand=True, padx=32, pady=(0,16))

        btn(self, "↻  Actualizar", color=BORDER, text_color=TEXT,
            command=self.cargar, width=140).pack(anchor="e", padx=32, pady=(0,20))

    def on_show(self): self.cargar()

    def cargar(self):
        rows = query("SELECT * FROM clientes ORDER BY nombre")
        self.tv.delete(*self.tv.get_children())
        for r in rows:
            self.tv.insert("", "end", values=(
                r["id"], r["nombre"], r["cedula"],
                r["telefono"] or "—", r["direccion"] or "—"))

    def agregar(self):
        n = self.e_nombre.get().strip()
        c = self.e_cedula.get().strip()
        t = self.e_tel.get().strip()
        d = self.e_dir.get().strip()
        if not n or not c:
            toast("Nombre y cédula son obligatorios", DANGER); return
        try:
            query("INSERT INTO clientes (nombre,cedula,telefono,direccion) VALUES (%s,%s,%s,%s)",
                  (n, c, t, d), fetch=False)
            toast("Cliente agregado")
            self.cargar()
        except Exception as e:
            toast(str(e), DANGER)

# ══════════════════════════════════════════════════════════════
#  TAB VENTAS
# ══════════════════════════════════════════════════════════════
class TabVentas(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.app   = app
        self.items = []
        self._build()

    def _build(self):
        # Formulario nueva venta
        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=6, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=32, pady=20)

        ctk.CTkLabel(card, text="NUEVA VENTA",
                     font=ctk.CTkFont("Georgia", 11, "bold"),
                     text_color=HEADER).pack(anchor="w", padx=20, pady=(16,4))

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=20)

        ctk.CTkLabel(top, text="PRODUCTO", text_color=MUTED,
                     font=ctk.CTkFont("Helvetica", 10)).grid(row=0, column=0, sticky="w")
        self.combo_prod = ctk.CTkComboBox(top, width=280, fg_color=BG,
                                           border_color=BORDER, text_color=TEXT,
                                           button_color=BORDER, dropdown_fg_color=SURFACE)
        self.combo_prod.grid(row=1, column=0, padx=(0,12))

        ctk.CTkLabel(top, text="CANTIDAD", text_color=MUTED,
                     font=ctk.CTkFont("Helvetica", 10)).grid(row=0, column=1, sticky="w")
        self.e_cant = ctk.CTkEntry(top, width=90, fg_color=BG,
                                    border_color=BORDER, text_color=TEXT)
        self.e_cant.insert(0, "1")
        self.e_cant.grid(row=1, column=1, padx=(0,12))

        ctk.CTkLabel(top, text="CLIENTE", text_color=MUTED,
                     font=ctk.CTkFont("Helvetica", 10)).grid(row=0, column=2, sticky="w")
        self.combo_cli = ctk.CTkComboBox(top, width=220, fg_color=BG,
                                          border_color=BORDER, text_color=TEXT,
                                          button_color=BORDER, dropdown_fg_color=SURFACE)
        self.combo_cli.grid(row=1, column=2, padx=(0,12))

        brow = ctk.CTkFrame(top, fg_color="transparent")
        brow.grid(row=1, column=3, padx=(8,0))
        btn(brow, "+ Ítem", color=BORDER, text_color=TEXT,
            command=self.agregar_item, width=90).pack(side="left", padx=4)
        btn(brow, "✔ Registrar", command=self.registrar, width=130).pack(side="left", padx=4)

        # Lista items
        self.items_frame = ctk.CTkScrollableFrame(card, fg_color="transparent", height=80)
        self.items_frame.pack(fill="x", padx=20, pady=8)

        self.lbl_total = ctk.CTkLabel(card, text="",
                                       font=ctk.CTkFont("Georgia", 16, "bold"),
                                       text_color=HEADER)
        self.lbl_total.pack(anchor="e", padx=20, pady=(0,16))

        # Historial
        tframe, self.tv = make_table(self,
            ["ID","Fecha","Cliente","Vendedor","Fuente","Total"],
            [50, 160, 160, 120, 80, 120])
        tframe.pack(fill="both", expand=True, padx=32, pady=(0,8))

        brow2 = ctk.CTkFrame(self, fg_color="transparent")
        brow2.pack(fill="x", padx=32, pady=(0,20))
        btn(brow2, "✕  Eliminar seleccionada", color=DANGER,
            command=self.eliminar, width=200).pack(side="left")
        btn(brow2, "↻  Actualizar", color=BORDER, text_color=TEXT,
            command=self.cargar_historial, width=140).pack(side="right")

    def on_show(self):
        self.cargar_selectores()
        self.cargar_historial()

    def cargar_selectores(self):
        prods = query("SELECT id,codigo,nombre,precio_unitario FROM productos WHERE activo=1")
        self._prod_map = {f"[{p['codigo']}] {p['nombre']}": p for p in prods}
        self.combo_prod.configure(values=list(self._prod_map.keys()))
        if prods: self.combo_prod.set(list(self._prod_map.keys())[0])

        clis = query("SELECT id,nombre,cedula FROM clientes")
        self._cli_map = {"— Sin cliente —": None}
        for c in clis:
            self._cli_map[f"{c['nombre']} ({c['cedula']})"] = c["id"]
        self.combo_cli.configure(values=list(self._cli_map.keys()))
        self.combo_cli.set("— Sin cliente —")

    def agregar_item(self):
        key = self.combo_prod.get()
        if key not in self._prod_map:
            toast("Selecciona un producto", DANGER); return
        prod     = self._prod_map[key]
        cantidad = int(self.e_cant.get() or 1)
        precio   = float(prod["precio_unitario"])
        subtotal = precio * cantidad
        self.items.append({"prod_id": prod["id"], "nombre": key,
                           "precio": precio, "cantidad": cantidad, "subtotal": subtotal})
        self._render_items()

    def _render_items(self):
        for w in self.items_frame.winfo_children(): w.destroy()
        total = sum(i["subtotal"] for i in self.items)
        for idx, it in enumerate(self.items):
            row = ctk.CTkFrame(self.items_frame, fg_color="#f0e8df", corner_radius=5)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=it["nombre"], text_color=TEXT,
                         font=ctk.CTkFont("DM Sans", 12)).pack(side="left", padx=12)
            ctk.CTkLabel(row, text=f"x{it['cantidad']}",
                         text_color=ACCENT2, font=ctk.CTkFont("Helvetica", 12, "bold")).pack(side="left", padx=8)
            ctk.CTkLabel(row, text=fmt_money(it["subtotal"]),
                         text_color=ACCENT, font=ctk.CTkFont("Helvetica", 12, "bold")).pack(side="left")
            ctk.CTkButton(row, text="✕", width=32, height=24, fg_color=DANGER,
                          text_color="#1a0505", corner_radius=6,
                          command=lambda i=idx: self._quitar(i)).pack(side="right", padx=8, pady=4)
        self.lbl_total.configure(text=f"Total: {fmt_money(total)}" if self.items else "")

    def _quitar(self, idx):
        self.items.pop(idx)
        self._render_items()

    def registrar(self):
        if not self.items:
            toast("Agrega al menos un ítem", DANGER); return
        cli_key = self.combo_cli.get()
        cli_id  = self._cli_map.get(cli_key)
        total   = sum(i["subtotal"] for i in self.items)

        uid = self.app.usuario["id"]
        vid = query("INSERT INTO ventas (cliente_id,usuario_id,fuente,total) VALUES (%s,%s,'app',%s)",
                    (cli_id, uid, total), fetch=False)
        for it in self.items:
            query("INSERT INTO detalle_ventas (venta_id,producto_id,cantidad,precio_unitario,subtotal) VALUES (%s,%s,%s,%s,%s)",
                  (vid, it["prod_id"], it["cantidad"], it["precio"], it["subtotal"]), fetch=False)

        toast(f"✔ Venta #{vid} — {fmt_money(total)}")
        self.items = []
        self._render_items()
        self.cargar_historial()

    def cargar_historial(self):
        rows = query("SELECT * FROM v_ventas ORDER BY fecha DESC LIMIT 100")
        self.tv.delete(*self.tv.get_children())
        for r in rows:
            self.tv.insert("", "end", values=(
                f"#{r['id']}", str(r["fecha"])[:16],
                r["cliente"] or "—", r["vendedor"],
                r["fuente"], fmt_money(r["total"])))

    def eliminar(self):
        sel = self.tv.selection()
        if not sel:
            toast("Selecciona una venta", DANGER); return
        vid = self.tv.item(sel[0])["values"][0].replace("#","")
        if messagebox.askyesno("Confirmar", f"¿Eliminar venta #{vid}?"):
            query(f"DELETE FROM ventas WHERE id={vid}", fetch=False)
            toast("Venta eliminada")
            self.cargar_historial()

# ══════════════════════════════════════════════════════════════
#  TAB ESTADÍSTICAS
# ══════════════════════════════════════════════════════════════
class TabEstadisticas(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="ESTADÍSTICAS",
                     font=ctk.CTkFont("Georgia", 11, "bold"),
                     text_color=HEADER).pack(anchor="w", padx=32, pady=(20,8))

        # Tarjetas resumen
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=32)

        # Top productos
        ctk.CTkLabel(self, text="TOP PRODUCTOS",
                     font=ctk.CTkFont("Helvetica", 10),
                     text_color=MUTED).pack(anchor="w", padx=32, pady=(16,4))
        tf, self.tv_top = make_table(self,
            ["#","Código","Nombre","Unidades","Ingresos"],
            [40, 80, 280, 100, 140])
        tf.pack(fill="both", expand=True, padx=32)

        # Por fuente
        ctk.CTkLabel(self, text="POR FUENTE",
                     font=ctk.CTkFont("Helvetica", 10),
                     text_color=MUTED).pack(anchor="w", padx=32, pady=(12,4))
        tf2, self.tv_fuente = make_table(self,
            ["Fuente","Cantidad","Total ingresos"], [120, 120, 180])
        tf2.pack(fill="x", padx=32)

        btn(self, "↻  Actualizar todo", color=BORDER, text_color=TEXT,
            command=self.cargar, width=180).pack(anchor="e", padx=32, pady=16)

    def on_show(self): self.cargar()

    def cargar(self):
        # Resumen
        hoy  = datetime.now().strftime("%Y-%m-%d")
        r1   = query(f"SELECT COUNT(*) AS t, COALESCE(SUM(total),0) AS ing FROM ventas WHERE DATE(fecha)='{hoy}'")[0]
        r2   = query("SELECT COUNT(*) AS t FROM ventas")[0]
        r3   = query("SELECT COUNT(*) AS t FROM clientes")[0]

        for w in self.stats_frame.winfo_children(): w.destroy()
        stats = [("VENTAS HOY", r1["t"]), ("INGRESOS HOY", fmt_money(r1["ing"])),
                 ("TOTAL VENTAS", r2["t"]), ("CLIENTES", r3["t"])]
        for label, val in stats:
            card = ctk.CTkFrame(self.stats_frame, fg_color="#faf7f4", corner_radius=5, border_width=1, border_color=BORDER)
            card.pack(side="left", expand=True, fill="x", padx=6)
            ctk.CTkLabel(card, text=label, text_color=MUTED,
                         font=ctk.CTkFont("Helvetica", 10)).pack(padx=16, pady=(14,4))
            ctk.CTkLabel(card, text=str(val), text_color=HEADER,
                         font=ctk.CTkFont("Georgia", 26, "bold")).pack(padx=16, pady=(0,14))

        # Top productos
        top = query("SELECT * FROM v_top_productos LIMIT 10")
        self.tv_top.delete(*self.tv_top.get_children())
        for i, r in enumerate(top, 1):
            self.tv_top.insert("", "end", values=(
                i, r["codigo"], r["nombre"],
                r["unidades_vendidas"], fmt_money(r["ingresos_totales"])))

        # Por fuente
        fuente = query("SELECT * FROM v_ventas_por_fuente")
        self.tv_fuente.delete(*self.tv_fuente.get_children())
        for r in fuente:
            self.tv_fuente.insert("", "end", values=(
                r["fuente"], r["cantidad_ventas"], fmt_money(r["total_ingresos"])))

# ══════════════════════════════════════════════════════════════
#  TAB USUARIOS
# ══════════════════════════════════════════════════════════════
class TabUsuarios(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=BG, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        card = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=6, border_width=1, border_color=BORDER)
        card.pack(fill="x", padx=32, pady=20)

        ctk.CTkLabel(card, text="CREAR USUARIO",
                     font=ctk.CTkFont("Georgia", 11, "bold"),
                     text_color=HEADER).pack(anchor="w", padx=20, pady=(16,4))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=20, pady=(0,16))
        form.columnconfigure((0,1,2,3,4), weight=1)

        self.e_nombre  = campo(form, "NOMBRE",     0, 0, "Juan")
        self.e_usuario = campo(form, "USUARIO",    0, 1, "juan01")
        self.e_pass    = campo(form, "CONTRASEÑA", 0, 2, "••••••", show="*")

        ctk.CTkLabel(form, text="ROL", text_color=MUTED,
                     font=ctk.CTkFont("Helvetica", 10)).grid(row=0, column=3, sticky="w", padx=(0,12), pady=(8,2))
        self.combo_rol = ctk.CTkComboBox(form, values=["vendedor","administrador"],
                                          fg_color="#faf7f4", border_color=BORDER, text_color=TEXT,
                                          button_color=BORDER, dropdown_fg_color=SURFACE)
        self.combo_rol.grid(row=1, column=3, sticky="ew", padx=(0,12))

        btn(form, "+ Crear", command=self.crear).grid(
            row=1, column=4, sticky="s", padx=(0,12), pady=(18,0))

        tframe, self.tv = make_table(self,
            ["ID","Nombre","Usuario","Rol","Activo"],
            [50, 200, 160, 140, 80])
        tframe.pack(fill="both", expand=True, padx=32, pady=(0,16))

        btn(self, "↻  Actualizar", color=BORDER, text_color=TEXT,
            command=self.cargar, width=140).pack(anchor="e", padx=32, pady=(0,20))

    def on_show(self): self.cargar()

    def cargar(self):
        rows = query("SELECT id,nombre,usuario,rol,activo FROM usuarios ORDER BY id")
        self.tv.delete(*self.tv.get_children())
        for r in rows:
            self.tv.insert("", "end", values=(
                r["id"], r["nombre"], r["usuario"],
                r["rol"], "✓" if r["activo"] else "✗"))

    def crear(self):
        n = self.e_nombre.get().strip()
        u = self.e_usuario.get().strip()
        p = self.e_pass.get()
        r = self.combo_rol.get()
        if not n or not u or not p:
            toast("Completa todos los campos", DANGER); return
        try:
            query("INSERT INTO usuarios (nombre,usuario,contrasena,rol) VALUES (%s,%s,%s,%s)",
                  (n, u, sha256(p), r), fetch=False)
            toast("Usuario creado")
            self.cargar()
        except Exception as e:
            toast(str(e), DANGER)



# ══════════════════════════════════════════════════════════════
#  LOGIN  (ventana independiente con tk.Tk puro)
# ══════════════════════════════════════════════════════════════
class LoginWindow(tk.Tk):
    """
    Ventana de login que corre ANTES de la app principal.
    Usa tk.Tk directamente para evitar conflictos con CTk.
    """
    def __init__(self):
        super().__init__()
        self.title("Iniciar sesión")
        self.resizable(False, False)
        self.configure(bg="#f5f0eb")
        self.usuario_logueado = None
        self._build()
        self._centrar(420, 500)

    def _centrar(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build(self):
        # ── Cabecera azul ─────────────────────────────────────
        cab = tk.Frame(self, bg="#2c3e50", height=100)
        cab.pack(fill="x")
        cab.pack_propagate(False)
        tk.Label(cab, text="◈  PaperPoint",
                 bg="#2c3e50", fg="#ffffff",
                 font=("Georgia", 20, "bold")).pack(pady=(20,2))
        tk.Label(cab, text="Sistema de Ventas",
                 bg="#2c3e50", fg="#b0c4d8",
                 font=("Helvetica", 11)).pack()

        # ── Formulario ────────────────────────────────────────
        form = tk.Frame(self, bg="#ffffff",
                        relief="solid", bd=1,
                        highlightbackground="#d5cdc4",
                        highlightthickness=1)
        form.pack(fill="x", padx=36, pady=28)

        tk.Label(form, text="Ingresa tus credenciales",
                 bg="#ffffff", fg="#8b7d6b",
                 font=("Helvetica", 11)).pack(pady=(18,14))

        # Usuario
        tk.Label(form, text="USUARIO",
                 bg="#ffffff", fg="#8b7d6b",
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=24)
        self.e_user = tk.Entry(form, font=("Helvetica", 13),
                                bg="#faf7f4", fg="#2c2416",
                                relief="solid", bd=1,
                                insertbackground="#2c2416")
        self.e_user.pack(fill="x", padx=24, ipady=8, pady=(3,14))

        # Contraseña
        tk.Label(form, text="CONTRASEÑA",
                 bg="#ffffff", fg="#8b7d6b",
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=24)
        self.e_pass = tk.Entry(form, font=("Helvetica", 13),
                                bg="#faf7f4", fg="#2c2416",
                                relief="solid", bd=1,
                                show="*", insertbackground="#2c2416")
        self.e_pass.pack(fill="x", padx=24, ipady=8, pady=(3,10))

        # Error
        self.lbl_err = tk.Label(form, text="",
                                 bg="#ffffff", fg="#e74c3c",
                                 font=("Helvetica", 10))
        self.lbl_err.pack(pady=(0,4))

        # Botón entrar
        btn_frame = tk.Frame(form, bg="#ffffff")
        btn_frame.pack(fill="x", padx=24, pady=(0,22))
        self.btn_entrar = tk.Button(btn_frame, text="Entrar",
                                     bg="#c0392b", fg="#ffffff",
                                     font=("Helvetica", 12, "bold"),
                                     relief="flat", cursor="hand2",
                                     activebackground="#a93226",
                                     activeforeground="#ffffff",
                                     pady=10,
                                     command=self.intentar_login)
        self.btn_entrar.pack(fill="x")

        # Footer
        tk.Label(self, text="Solo usuarios registrados pueden acceder.",
                 bg="#f5f0eb", fg="#8b7d6b",
                 font=("Helvetica", 9)).pack(pady=(0,16))

        # Bindings
        self.bind("<Return>", lambda e: self.intentar_login())
        self.e_user.focus_set()

        # Hover botón
        self.btn_entrar.bind("<Enter>", lambda e: self.btn_entrar.configure(bg="#a93226"))
        self.btn_entrar.bind("<Leave>", lambda e: self.btn_entrar.configure(bg="#c0392b"))

    def intentar_login(self):
        usuario = self.e_user.get().strip()
        passwd  = self.e_pass.get()

        if not usuario or not passwd:
            self.lbl_err.configure(text="Completa usuario y contraseña")
            return

        self.btn_entrar.configure(text="Verificando...", state="disabled")
        self.update()

        try:
            rows = query(
                "SELECT id, nombre, rol FROM usuarios "
                "WHERE usuario=%s AND contrasena=%s AND activo=1",
                (usuario, sha256(passwd))
            )
        except Exception as e:
            self.lbl_err.configure(text=f"Error de conexión: {e}")
            self.btn_entrar.configure(text="Entrar", state="normal")
            return

        if not rows:
            self.lbl_err.configure(text="Usuario o contraseña incorrectos")
            self.e_pass.delete(0, "end")
            self.btn_entrar.configure(text="Entrar", state="normal")
            return

        self.usuario_logueado = rows[0]
        self.destroy()


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    while True:
        # 1. Mostrar login
        login = LoginWindow()
        login.mainloop()

        # 2. Si cerró sin loguearse → salir
        if not login.usuario_logueado:
            break

        # 3. Abrir app principal
        app = App(login.usuario_logueado)
        app.mainloop()

        # 4. Si la app termina (cerrar sesión) vuelve al login
        # El loop continúa solo si _reiniciar es True
        if not getattr(app, "_reiniciar", False):
            break