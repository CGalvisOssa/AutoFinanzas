import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import json
import os
from datetime import datetime
from collections import Counter, defaultdict
import numpy as np
import threading

try:
    from openai import OpenAI
    OPENAI_OK = True
except:
    OPENAI_OK = False

class AppFinanciera:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema de Gestión Financiera")
        self.root.geometry("1100x700")
        self.root.configure(bg="#2b2b2b")
        
        self.credentials_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
        self.cargar_credenciales()
        
        self.openai_client = None
        if OPENAI_OK and self.openai_key and len(self.openai_key) > 10:
            try:
                self.openai_client = OpenAI(api_key=self.openai_key)
                print("✓ OpenAI conectado")
            except Exception as e:
                print(f"⚠ Error OpenAI: {e}")
        
        if not os.path.exists(self.carpeta):
            os.makedirs(self.carpeta)
        
        self.setup_ui()
    
    def cargar_credenciales(self):
        try:
            with open(self.credentials_path, 'r', encoding='utf-8') as f:
                creds = json.load(f)
            self.openai_key = creds.get('openai', {}).get('api_key', '')
            self.esp32_ip = creds.get('esp32', {}).get('ip', '192.168.1.100')
            self.carpeta = "reportes"
            print(f"✓ Credenciales cargadas")
        except:
            self.openai_key = ""
            self.esp32_ip = "192.168.1.100"
            self.carpeta = "reportes"
    
    def guardar_credenciales(self):
        try:
            with open(self.credentials_path, 'r', encoding='utf-8') as f:
                creds = json.load(f)
            if 'esp32' not in creds:
                creds['esp32'] = {}
            creds['esp32']['ip'] = self.esp32_ip
            with open(self.credentials_path, 'w', encoding='utf-8') as f:
                json.dump(creds, f, indent=2, ensure_ascii=False)
            return True
        except:
            return False
        
    def setup_ui(self):
        tk.Label(self.root, text="📊 Sistema de Gestión Financiera", 
                font=("Arial", 16, "bold"), bg="#1e1e1e", fg="white", 
                pady=15).pack(fill=tk.X)
        
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#2b2b2b')
        style.configure('TNotebook.Tab', background='#3c3c3c', foreground='white', 
                       padding=[15, 8], font=('Arial', 9))
        style.map('TNotebook.Tab', background=[('selected', '#1e1e1e')])
        
        self.tab_esp32(notebook)
        self.tab_chat(notebook)
        self.tab_estadisticas(notebook)
        
    def tab_esp32(self, notebook):
        tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(tab, text="📡 ESP32")
        
        frame_ip = tk.Frame(tab, bg="#1e1e1e")
        frame_ip.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Label(frame_ip, text="IP del ESP32:", bg="#1e1e1e", fg="white",
                font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        
        self.entry_ip = tk.Entry(frame_ip, font=("Arial", 11), width=20)
        self.entry_ip.insert(0, self.esp32_ip)
        self.entry_ip.pack(side=tk.LEFT, padx=5)
        
        tk.Button(frame_ip, text="💾 Guardar IP", command=self.guardar_ip,
                 bg="#4CAF50", fg="white", font=("Arial", 9, "bold"), 
                 cursor="hand2", padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(tab, text="📥 OBTENER REPORTE DEL ESP32", 
                 command=self.obtener_reporte, bg="#2196F3", fg="white",
                 font=("Arial", 12, "bold"), cursor="hand2",
                 padx=30, pady=20).pack(pady=30)
        
        tk.Label(tab, text="📁 Reportes Guardados", bg="#2b2b2b", fg="white",
                font=("Arial", 11, "bold")).pack(pady=10)
        
        frame_lista = tk.Frame(tab, bg="#1e1e1e")
        frame_lista.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        scroll = tk.Scrollbar(frame_lista)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.lista_reportes = tk.Listbox(frame_lista, bg="#0d0d0d", fg="white",
                                         font=("Consolas", 9), yscrollcommand=scroll.set)
        self.lista_reportes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.lista_reportes.yview)
        
        tk.Button(tab, text="🔄 Actualizar", command=self.actualizar_lista,
                 bg="#FF9800", fg="white", font=("Arial", 9, "bold"),
                 cursor="hand2", padx=20, pady=5).pack(pady=10)
        
        self.actualizar_lista()
    
    def tab_chat(self, notebook):
        tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(tab, text="💬 Chat IA")
        
        if not OPENAI_OK or not self.openai_client:
            mensaje = "⚠ OpenAI no configurado\n\n"
            if not OPENAI_OK:
                mensaje += "Instala: pip install openai"
            else:
                mensaje += "Edita credentials.json:\n"
                mensaje += '"openai": {"api_key": "sk-..."}'
            tk.Label(tab, text=mensaje, bg="#2b2b2b", fg="#FF9800", 
                    font=("Consolas", 10), justify=tk.LEFT).pack(expand=True, pady=50)
            return
        
        # Barra de preguntas personalizadas
        frame_preguntas = tk.Frame(tab, bg="#1e1e1e")
        frame_preguntas.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(frame_preguntas, text="🔍 Pregunta específica:", 
                bg="#1e1e1e", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        self.pregunta_entry = tk.Entry(frame_preguntas, font=("Arial", 10), 
                                      bg="#0d0d0d", fg="white", width=50,
                                      insertbackground="white")
        self.pregunta_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.pregunta_entry.bind('<Return>', lambda e: self.hacer_pregunta_especifica())
        
        tk.Button(frame_preguntas, text="📤 Preguntar", 
                 command=self.hacer_pregunta_especifica,
                 bg="#2196F3", fg="white", font=("Arial", 9, "bold"),
                 cursor="hand2", padx=15).pack(side=tk.RIGHT, padx=5)
        
        # Panel superior con estadísticas básicas
        panel_stats = tk.Frame(tab, bg="#1e1e1e", height=150)
        panel_stats.pack(fill=tk.X, padx=10, pady=10)
        panel_stats.pack_propagate(False)
        
        tk.Label(panel_stats, text="📊 Resumen de Tu Negocio", bg="#1e1e1e", fg="white",
                font=("Arial", 11, "bold")).pack(pady=5)
        
        self.label_stats = tk.Label(panel_stats, text="Cargando...", bg="#1e1e1e", 
                                    fg="#aaaaaa", font=("Consolas", 9), justify=tk.LEFT)
        self.label_stats.pack(pady=5)
        
        # Ejemplos de preguntas
        frame_ejemplos = tk.Frame(tab, bg="#1e1e1e")
        frame_ejemplos.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(frame_ejemplos, text="💡 Preguntas que puedes hacer:", 
                bg="#1e1e1e", fg="white", font=("Arial", 9, "bold")).pack(anchor="w", padx=10, pady=5)
        
        ejemplos = [
            "¿Cuál es mi producto más vendido?",
            "¿Cuánto vendí esta semana?",
            "Dame recomendaciones para mejorar las ventas",
            "¿Qué días vendo más?",
            "Analiza mis tendencias de venta"
        ]
        
        for ej in ejemplos:
            btn = tk.Button(frame_ejemplos, text=ej, command=lambda e=ej: self.preguntar_ejemplo(e),
                           bg="#3c3c3c", fg="white", font=("Arial", 8), 
                           cursor="hand2", anchor="w", padx=10, pady=3)
            btn.pack(fill=tk.X, padx=10, pady=2)
        
        # Chat
        self.chat_text = scrolledtext.ScrolledText(tab, bg="#0d0d0d", fg="white",
                                                   font=("Arial", 10), wrap=tk.WORD,
                                                   state=tk.DISABLED)
        self.chat_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.chat_text.tag_config("user", foreground="#4CAF50", font=("Arial", 10, "bold"))
        self.chat_text.tag_config("ia", foreground="#2196F3", font=("Arial", 10, "bold"))
        
        # Input
        frame_input = tk.Frame(tab, bg="#1e1e1e")
        frame_input.pack(fill=tk.X, padx=10, pady=10)
        
        self.chat_entry = tk.Entry(frame_input, font=("Arial", 11), bg="#0d0d0d",
                                   fg="white", insertbackground="white")
        self.chat_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.chat_entry.bind('<Return>', lambda e: self.enviar_chat())
        
        tk.Button(frame_input, text="📤", command=self.enviar_chat,
                 bg="#2196F3", fg="white", font=("Arial", 12, "bold"),
                 cursor="hand2", padx=15).pack(side=tk.RIGHT)
        
        self.agregar_chat("IA", "¡Hola! Soy tu asistente financiero. Pregúntame sobre tus ventas 😊", "ia")
        self.actualizar_stats_basicas()
    
    def tab_estadisticas(self, notebook):
        tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(tab, text="📈 Estadísticas Avanzadas")
        
        frame_btn = tk.Frame(tab, bg="#1e1e1e")
        frame_btn.pack(fill=tk.X, padx=20, pady=20)
        
        tk.Button(frame_btn, text="📊 Calcular Estadísticas", 
                 command=self.mostrar_stats, bg="#4CAF50", fg="white",
                 font=("Arial", 10, "bold"), cursor="hand2",
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        tk.Button(frame_btn, text="📈 Ver Gráficas", 
                 command=self.mostrar_graficas, bg="#2196F3", fg="white",
                 font=("Arial", 10, "bold"), cursor="hand2",
                 padx=20, pady=10).pack(side=tk.LEFT, padx=5)
        
        self.text_stats = scrolledtext.ScrolledText(tab, bg="#0d0d0d", fg="white",
                                                    font=("Consolas", 9), wrap=tk.WORD)
        self.text_stats.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    # ========== FUNCIONES ESP32 ==========
    
    def guardar_ip(self):
        self.esp32_ip = self.entry_ip.get().strip()
        if self.guardar_credenciales():
            messagebox.showinfo("✓", f"IP guardada\n{self.esp32_ip}")
        else:
            messagebox.showwarning("⚠", f"IP guardada en memoria\n{self.esp32_ip}")
    
    def obtener_reporte(self):
        def obtener():
            try:
                url = f"http://{self.esp32_ip}/reporte"
                resp = requests.get(url, timeout=10)
                
                if resp.status_code == 200:
                    datos = resp.json()
                    fecha = datos.get('fecha', datetime.now().strftime('%Y-%m-%d'))
                    hora = datetime.now().strftime('%H%M%S')
                    nombre = f"reporte_{fecha}_{hora}.json"
                    
                    with open(os.path.join(self.carpeta, nombre), 'w', encoding='utf-8') as f:
                        json.dump(datos, f, indent=2, ensure_ascii=False)
                    
                    self.actualizar_lista()
                    self.actualizar_stats_basicas()
                    messagebox.showinfo("✓", f"Reporte guardado\nVentas: {datos.get('total_ventas', 0)}\nTotal: ${datos.get('total_dia', 0):,}")
                else:
                    messagebox.showerror("Error", f"HTTP {resp.status_code}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo conectar:\n{str(e)}")
        
        threading.Thread(target=obtener, daemon=True).start()
    
    def actualizar_lista(self):
        self.lista_reportes.delete(0, tk.END)
        if os.path.exists(self.carpeta):
            archivos = sorted([f for f in os.listdir(self.carpeta) if f.endswith('.json')], reverse=True)
            for a in archivos:
                self.lista_reportes.insert(tk.END, a)
    
    # ========== FUNCIONES ESTADÍSTICAS ==========
    
    def cargar_datos(self):
        datos = []
        if not os.path.exists(self.carpeta):
            return datos
        
        for archivo in os.listdir(self.carpeta):
            if archivo.endswith('.json'):
                try:
                    with open(os.path.join(self.carpeta, archivo), 'r', encoding='utf-8') as f:
                        datos.append(json.load(f))
                except:
                    continue
        return datos
    
    def calcular_stats(self):
        datos = self.cargar_datos()
        if not datos:
            return None
        
        ingresos = [d.get('total_dia', 0) for d in datos]
        productos = []
        for r in datos:
            for v in r.get('ventas', []):
                productos.append(v.get('producto', 'N/A'))
        
        por_mes = defaultdict(lambda: {'ingresos': 0})
        for r in datos:
            mes = r.get('fecha', '2000-01')[:7]
            por_mes[mes]['ingresos'] += r.get('total_dia', 0)
        
        moda = Counter(productos).most_common(1)[0] if productos else ('N/A', 0)
        
        return {
            'media': np.mean(ingresos),
            'mediana': np.median(ingresos),
            'moda': moda,
            'p25': np.percentile(ingresos, 25),
            'p50': np.percentile(ingresos, 50),
            'p75': np.percentile(ingresos, 75),
            'prom_dia': np.mean(ingresos),
            'prom_mes': np.mean([m['ingresos'] for m in por_mes.values()]),
            'desv': np.std(ingresos),
            'total': sum(ingresos),
            'datos': datos,
            'ingresos': ingresos,
            'por_mes': por_mes,
            'productos': productos
        }
    
    def actualizar_stats_basicas(self):
        """Actualiza las estadísticas básicas en el panel del chat"""
        datos = self.cargar_datos()
        if not datos:
            texto = "No hay datos aún. Obtén un reporte del ESP32."
            self.label_stats.config(text=texto)
            return
        
        # Calcular estadísticas mejoradas
        total_ingresos = sum(d.get('total_dia', 0) for d in datos)
        total_dias = len(datos)
        promedio_dia = total_ingresos / total_dias if total_dias > 0 else 0
        
        # Contar productos
        productos_counter = Counter()
        for reporte in datos:
            for venta in reporte.get('ventas', []):
                producto = venta.get('producto', 'Desconocido')
                cantidad = venta.get('cantidad', 1)
                productos_counter[producto] += cantidad
        
        producto_top = productos_counter.most_common(1)[0] if productos_counter else ('N/A', 0)
        
        texto = f"""
Total acumulado: ${total_ingresos:,.0f} COP
Promedio por día: ${promedio_dia:,.0f} COP
Días registrados: {total_dias}
Producto estrella: {producto_top[0]}
Unidades vendidas: {producto_top[1]}
        """.strip()
        
        self.label_stats.config(text=texto)
    
    def mostrar_stats(self):
        stats = self.calcular_stats()
        if not stats:
            self.text_stats.delete(1.0, tk.END)
            self.text_stats.insert(tk.END, "⚠ No hay datos")
            return
        
        texto = f"""
╔════════════════════════════════════════════════════╗
║          ESTADÍSTICAS FINANCIERAS                  ║
╚════════════════════════════════════════════════════╝

📊 TENDENCIA CENTRAL
────────────────────────────────────────────────────
  Media:           ${stats['media']:>15,.0f} COP
  Mediana:         ${stats['mediana']:>15,.0f} COP
  Moda:            {stats['moda'][0][:25]:>25s}
                   ({stats['moda'][1]} ventas)

📈 PERCENTILES
────────────────────────────────────────────────────
  25% (Q1):        ${stats['p25']:>15,.0f} COP
  50% (Q2):        ${stats['p50']:>15,.0f} COP
  75% (Q3):        ${stats['p75']:>15,.0f} COP

💰 PROMEDIOS
────────────────────────────────────────────────────
  Por día:         ${stats['prom_dia']:>15,.0f} COP
  Por mes:         ${stats['prom_mes']:>15,.0f} COP

📉 DISPERSIÓN
────────────────────────────────────────────────────
  Desv. Estándar:  ${stats['desv']:>15,.0f} COP

🎯 TOTALES
────────────────────────────────────────────────────
  Total periodo:   ${stats['total']:>15,.0f} COP
  Días:            {len(stats['datos']):>23d}

╚════════════════════════════════════════════════════╝
"""
        self.text_stats.delete(1.0, tk.END)
        self.text_stats.insert(tk.END, texto)
    
    def mostrar_graficas(self):
        stats = self.calcular_stats()
        if not stats:
            messagebox.showwarning("⚠", "No hay datos")
            return
        
        ventana = tk.Toplevel(self.root)
        ventana.title("📈 Gráficas Estadísticas")
        ventana.geometry("1000x700")
        ventana.configure(bg="#2b2b2b")
        
        fig = plt.Figure(figsize=(10, 7), facecolor='#1e1e1e')
        
        ax1 = fig.add_subplot(2, 3, 1, facecolor='#2b2b2b')
        ax1.plot(stats['ingresos'], marker='o', color='#4CAF50', linewidth=2)
        ax1.set_title('💰 Ingresos Diarios', color='white')
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(colors='white')
        
        ax2 = fig.add_subplot(2, 3, 2, facecolor='#2b2b2b')
        meses = sorted(stats['por_mes'].keys())
        ing_mes = [stats['por_mes'][m]['ingresos'] for m in meses]
        ax2.bar(range(len(meses)), ing_mes, color='#2196F3')
        ax2.set_title('📅 Por Mes', color='white')
        ax2.tick_params(colors='white')
        
        ax3 = fig.add_subplot(2, 3, 3, facecolor='#2b2b2b')
        ax3.boxplot(stats['ingresos'], patch_artist=True,
                   boxprops=dict(facecolor='#FF9800', alpha=0.7))
        ax3.set_title('📦 Percentiles', color='white')
        ax3.tick_params(colors='white')
        
        ax4 = fig.add_subplot(2, 3, 4, facecolor='#2b2b2b')
        top5 = Counter(stats['productos']).most_common(5)
        prods = [p[0][:12] for p in top5]
        vals = [p[1] for p in top5]
        ax4.barh(prods, vals, color='#9C27B0')
        ax4.set_title('🏆 Top Productos', color='white')
        ax4.invert_yaxis()
        ax4.tick_params(colors='white')
        
        ax5 = fig.add_subplot(2, 3, 5, facecolor='#2b2b2b')
        ax5.axis('off')
        texto = f"""
Media: ${stats['media']:,.0f}
Mediana: ${stats['mediana']:,.0f}

P25: ${stats['p25']:,.0f}
P75: ${stats['p75']:,.0f}

Prom/día: ${stats['prom_dia']:,.0f}
Prom/mes: ${stats['prom_mes']:,.0f}
        """
        ax5.text(0.1, 0.9, texto, transform=ax5.transAxes, fontsize=9,
                verticalalignment='top', fontfamily='monospace', color='white')
        
        ax6 = fig.add_subplot(2, 3, 6, facecolor='#2b2b2b')
        ax6.axis('off')
        moda_txt = f"""
MODA
(Más Frecuente)

{stats['moda'][0][:18]}

{stats['moda'][1]} ventas
        """
        ax6.text(0.5, 0.5, moda_txt, transform=ax6.transAxes, fontsize=11,
                ha='center', va='center', color='#4CAF50', fontweight='bold')
        
        canvas = FigureCanvasTkAgg(fig, ventana)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    # ========== FUNCIONES CHAT ==========
    
    def generar_contexto_ia(self):
        """Genera un contexto detallado para la IA con información de productos"""
        datos = self.cargar_datos()
        if not datos:
            return "No hay datos de ventas disponibles."
        
        contexto = "=== DATOS DETALLADOS DE VENTAS ===\n\n"
        
        # Estadísticas generales
        total_ventas = sum(d.get('total_ventas', 0) for d in datos)
        total_ingresos = sum(d.get('total_dia', 0) for d in datos)
        
        contexto += f"ESTADÍSTICAS GENERALES:\n"
        contexto += f"- Total de días con ventas: {len(datos)}\n"
        contexto += f"- Total de transacciones: {total_ventas}\n"
        contexto += f"- Ingresos totales: ${total_ingresos:,} COP\n"
        contexto += f"- Promedio diario: ${total_ingresos/len(datos):,.0f} COP\n\n"
        
        # Análisis de productos
        productos_counter = Counter()
        ingresos_por_producto = defaultdict(int)
        
        for reporte in datos:
            for venta in reporte.get('ventas', []):
                producto = venta.get('producto', 'Desconocido')
                cantidad = venta.get('cantidad', 1)
                valor = venta.get('valor', 0)
                
                productos_counter[producto] += cantidad
                ingresos_por_producto[producto] += valor
        
        contexto += "PRODUCTOS MÁS VENDIDOS (por unidades):\n"
        for producto, unidades in productos_counter.most_common(10):
            contexto += f"- {producto}: {unidades} unidades (${ingresos_por_producto[producto]:,} COP)\n"
        
        contexto += "\nDETALLE POR DÍA:\n"
        for reporte in datos[-10:]:  # Últimos 10 días
            fecha = reporte.get('fecha', 'N/A')
            total_dia = reporte.get('total_dia', 0)
            ventas_dia = reporte.get('total_ventas', 0)
            
            contexto += f"\n📅 {fecha}: {ventas_dia} ventas, Total: ${total_dia:,} COP\n"
            
            for venta in reporte.get('ventas', []):
                producto = venta.get('producto', 'N/A')
                cantidad = venta.get('cantidad', 1)
                valor = venta.get('valor', 0)
                contexto += f"   - {producto}: {cantidad} und × ${valor//cantidad:,} = ${valor:,}\n"
        
        return contexto
    
    def agregar_chat(self, usuario, msg, tag):
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"\n{usuario}: ", tag)
        self.chat_text.insert(tk.END, f"{msg}\n")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)
    
    def preguntar_ejemplo(self, pregunta):
        """Inserta pregunta de ejemplo en el chat"""
        self.chat_entry.delete(0, tk.END)
        self.chat_entry.insert(0, pregunta)
        self.enviar_chat()
    
    def enviar_chat(self):
        msg = self.chat_entry.get().strip()
        if not msg:
            return
        
        self.chat_entry.delete(0, tk.END)
        self.agregar_chat("Tú", msg, "user")
        
        def procesar():
            try:
                contexto = self.generar_contexto_ia()
                
                resp = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f"""Eres un asistente financiero experto en análisis de ventas de papelería. 
                        
                        DATOS DISPONIBLES:
                        {contexto}
                        
                        INSTRUCCIONES:
                        1. Para 'producto más vendido' cuenta UNIDADES, no valor
                        2. Sé específico con nombres de productos y cantidades
                        3. Da recomendaciones prácticas basadas en los datos
                        4. Usa emojis para hacerlo amigable
                        5. Menciona valores en pesos colombianos (COP)"""},
                        {"role": "user", "content": msg}
                    ],
                    max_tokens=800,
                    temperature=0.7
                )
                
                respuesta = resp.choices[0].message.content
                self.agregar_chat("IA", respuesta, "ia")
            except Exception as e:
                self.agregar_chat("Sistema", f"Error: {str(e)}", "ia")
        
        threading.Thread(target=procesar, daemon=True).start()
    
    # ========== FUNCIONES BARRA DE PREGUNTAS ESPECÍFICAS ==========
    
    def hacer_pregunta_especifica(self):
        pregunta = self.pregunta_entry.get().strip()
        if not pregunta:
            return
        
        self.pregunta_entry.delete(0, tk.END)
        self.agregar_chat("Tú", f"[Específica] {pregunta}", "user")
        
        def procesar():
            try:
                contexto = self.generar_contexto_ia()
                
                resp = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f"""Eres un analista financiero especializado. Responde de forma CONCISA y DIRECTA.

DATOS:
{contexto}

Responde máximo 3 párrafos enfocándote solo en lo esencial."""},
                        {"role": "user", "content": pregunta}
                    ],
                    max_tokens=400,
                    temperature=0.5
                )
                
                respuesta = resp.choices[0].message.content
                self.agregar_chat("IA", respuesta, "ia")
            except Exception as e:
                self.agregar_chat("Sistema", f"Error: {str(e)}", "ia")
        
        threading.Thread(target=procesar, daemon=True).start()


def main():
    root = tk.Tk()
    app = AppFinanciera(root)
    root.mainloop()

if __name__ == "__main__":
    main()