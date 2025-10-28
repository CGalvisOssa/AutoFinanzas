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
        
        # Ruta del archivo de credenciales (archivo en la misma carpeta que este script)
        # Usar ruta relativa hace que funcione aunque muevas el proyecto de máquina
        self.credentials_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
        
        # Cargar configuración desde credentials.json
        self.cargar_credenciales()
        
        # Servicios
        self.openai_client = None
        if OPENAI_OK and self.openai_key and len(self.openai_key) > 10:
            try:
                self.openai_client = OpenAI(api_key=self.openai_key)
                print("✓ OpenAI conectado desde credentials.json")
            except Exception as e:
                print(f"⚠ Error OpenAI: {e}")
        
        if not os.path.exists(self.carpeta):
            os.makedirs(self.carpeta)
        
        self.setup_ui()
    
    def cargar_credenciales(self):
        """Carga configuración desde credentials.json"""
        try:
            with open(self.credentials_path, 'r', encoding='utf-8') as f:
                creds = json.load(f)
            
            self.openai_key = creds.get('openai', {}).get('api_key', '')
            self.esp32_ip = creds.get('esp32', {}).get('ip', '192.168.1.100')
            self.carpeta = "reportes"
            
            print(f"✓ Credenciales cargadas desde: {self.credentials_path}")
            print(f"  - ESP32 IP: {self.esp32_ip}")
            print(f"  - OpenAI: {'Configurado' if self.openai_key and self.openai_key != 'TU_API_KEY_DE_OPENAI_AQUI' else 'No configurado'}")
            
        except FileNotFoundError:
            # No crear el archivo automáticamente — usar valores por defecto y avisar al usuario
            print(f"⚠ No se encontró credentials.json en: {self.credentials_path}")
            print("  Usando valores por defecto. Para habilitar OpenAI edita el archivo credentials.json en la ruta mostrada.")
            self.openai_key = ""
            self.esp32_ip = "192.168.1.100"
            self.carpeta = "reportes"
        except Exception as e:
            print(f"⚠ Error al cargar credentials: {e}")
            self.openai_key = ""
            self.esp32_ip = "192.168.1.100"
            self.carpeta = "reportes"
    
    def guardar_credenciales(self):
        """Guarda la configuración actualizada en credentials.json"""
        try:
            # Leer el archivo completo
            with open(self.credentials_path, 'r', encoding='utf-8') as f:
                creds = json.load(f)
            
            # Actualizar valores
            if 'esp32' not in creds:
                creds['esp32'] = {}
            creds['esp32']['ip'] = self.esp32_ip
            
            # Guardar
            with open(self.credentials_path, 'w', encoding='utf-8') as f:
                json.dump(creds, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Credenciales guardadas")
            return True
        except Exception as e:
            print(f"⚠ Error al guardar: {e}")
            return False
        
    def setup_ui(self):
        # Título
        tk.Label(self.root, text="📊 Sistema de Gestión Financiera", 
                font=("Arial", 16, "bold"), bg="#1e1e1e", fg="white", 
                pady=15).pack(fill=tk.X)
        
        # Pestañas
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook', background='#2b2b2b')
        style.configure('TNotebook.Tab', background='#3c3c3c', foreground='white', 
                       padding=[15, 8], font=('Arial', 9))
        style.map('TNotebook.Tab', background=[('selected', '#1e1e1e')])
        
        self.tab_esp32(notebook)
        self.tab_estadisticas(notebook)
        self.tab_chat(notebook)
        
    def tab_esp32(self, notebook):
        tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(tab, text="📡 ESP32")
        
        # Config IP
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
        
        # Botón obtener reporte
        tk.Button(tab, text="📥 OBTENER REPORTE DEL ESP32", 
                 command=self.obtener_reporte, bg="#2196F3", fg="white",
                 font=("Arial", 12, "bold"), cursor="hand2",
                 padx=30, pady=20).pack(pady=30)
        
        # Lista de reportes
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
    
    def tab_estadisticas(self, notebook):
        tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(tab, text="📊 Estadísticas")
        
        # Botones
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
        
        # Área de resultados
        self.text_stats = scrolledtext.ScrolledText(tab, bg="#0d0d0d", fg="white",
                                                    font=("Consolas", 9), wrap=tk.WORD)
        self.text_stats.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    def tab_chat(self, notebook):
        tab = tk.Frame(notebook, bg="#2b2b2b")
        notebook.add(tab, text="💬 Chat IA")
        
        if not OPENAI_OK or not self.openai_client:
            mensaje = "⚠ OpenAI no configurado\n\n"
            if not OPENAI_OK:
                mensaje += "Instala: pip install openai"
            else:
                mensaje += "Edita credentials.json y agrega tu API key:\n\n"
                mensaje += '"openai": {\n'
                mensaje += '  "api_key": "sk-tu-key-aqui"\n'
                mensaje += '}'
            
            tk.Label(tab, text=mensaje, bg="#2b2b2b", fg="#FF9800", 
                    font=("Consolas", 10), justify=tk.LEFT).pack(expand=True, pady=50)
            return
        
        # Estado
        tk.Label(tab, text="✓ OpenAI Conectado", bg="#1e1e1e", fg="#4CAF50",
                font=("Arial", 10, "bold"), pady=10).pack(fill=tk.X)
        
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
        
        self.agregar_chat("IA", "Hola! Pregúntame sobre tus ventas 😊", "ia")
    
    # ========== FUNCIONES ESP32 ==========
    
    def guardar_ip(self):
        self.esp32_ip = self.entry_ip.get().strip()
        
        # Guardar en credentials.json
        if self.guardar_credenciales():
            messagebox.showinfo("✓", f"IP guardada en credentials.json\n{self.esp32_ip}")
        else:
            messagebox.showwarning("⚠", f"IP guardada solo en memoria\n{self.esp32_ip}")
    
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
        
        # Crear ventana nueva
        ventana = tk.Toplevel(self.root)
        ventana.title("📈 Gráficas Estadísticas")
        ventana.geometry("1000x700")
        ventana.configure(bg="#2b2b2b")
        
        fig = plt.Figure(figsize=(10, 7), facecolor='#1e1e1e')
        
        # 1. Ingresos diarios
        ax1 = fig.add_subplot(2, 3, 1, facecolor='#2b2b2b')
        ax1.plot(stats['ingresos'], marker='o', color='#4CAF50', linewidth=2)
        ax1.set_title('💰 Ingresos Diarios', color='white')
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(colors='white')
        
        # 2. Ingresos mensuales
        ax2 = fig.add_subplot(2, 3, 2, facecolor='#2b2b2b')
        meses = sorted(stats['por_mes'].keys())
        ing_mes = [stats['por_mes'][m]['ingresos'] for m in meses]
        ax2.bar(range(len(meses)), ing_mes, color='#2196F3')
        ax2.set_title('📅 Por Mes', color='white')
        ax2.tick_params(colors='white')
        
        # 3. Box plot
        ax3 = fig.add_subplot(2, 3, 3, facecolor='#2b2b2b')
        ax3.boxplot(stats['ingresos'], patch_artist=True,
                   boxprops=dict(facecolor='#FF9800', alpha=0.7))
        ax3.set_title('📦 Percentiles', color='white')
        ax3.tick_params(colors='white')
        
        # 4. Top productos
        ax4 = fig.add_subplot(2, 3, 4, facecolor='#2b2b2b')
        top5 = Counter(stats['productos']).most_common(5)
        prods = [p[0][:12] for p in top5]
        vals = [p[1] for p in top5]
        ax4.barh(prods, vals, color='#9C27B0')
        ax4.set_title('🏆 Top Productos', color='white')
        ax4.invert_yaxis()
        ax4.tick_params(colors='white')
        
        # 5. Stats
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
        
        # 6. Moda
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
    
    def agregar_chat(self, usuario, msg, tag):
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.insert(tk.END, f"\n{usuario}: ", tag)
        self.chat_text.insert(tk.END, f"{msg}\n")
        self.chat_text.see(tk.END)
        self.chat_text.config(state=tk.DISABLED)
    
    def enviar_chat(self):
        msg = self.chat_entry.get().strip()
        if not msg:
            return
        
        self.chat_entry.delete(0, tk.END)
        self.agregar_chat("Tú", msg, "user")
        
        def procesar():
            try:
                datos = self.cargar_datos()
                contexto = "Datos de ventas:\n"
                for d in datos:
                    contexto += f"Fecha {d.get('fecha')}: ${d.get('total_dia'):,} COP\n"
                
                resp = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f"Eres un asistente financiero. Datos:\n{contexto}"},
                        {"role": "user", "content": msg}
                    ],
                    max_tokens=500
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