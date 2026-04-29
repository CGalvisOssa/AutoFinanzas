import matplotlib.pyplot as plt
import json
import os
from datetime import datetime
from collections import defaultdict, Counter
import numpy as np

class AnalizadorFinanciero:
    def __init__(self, carpeta_reportes="reportes"):
        self.carpeta_reportes = carpeta_reportes
        self.datos = []
        self.cargar_datos()
        
        plt.style.use('dark_background')
        plt.rcParams['figure.facecolor'] = '#1e1e1e'
        plt.rcParams['axes.facecolor'] = '#2b2b2b'
        
    def cargar_datos(self):
        """Carga todos los reportes JSON"""
        self.datos = []
        if not os.path.exists(self.carpeta_reportes):
            return
        
        archivos = [f for f in os.listdir(self.carpeta_reportes) if f.endswith('.json')]
        for archivo in archivos:
            try:
                ruta = os.path.join(self.carpeta_reportes, archivo)
                with open(ruta, 'r', encoding='utf-8') as f:
                    self.datos.append(json.load(f))
            except:
                continue
        
        self.datos.sort(key=lambda x: x.get('fecha', '0000-00-00'))
    
    def calcular_estadisticas(self):
        """Calcula todas las estadísticas necesarias"""
        if not self.datos:
            return None
        
        # Datos básicos
        ingresos = [d.get('total_dia', 0) for d in self.datos]
        ventas = [d.get('total_ventas', 0) for d in self.datos]
        
        # Productos
        productos = []
        for r in self.datos:
            for v in r.get('ventas', []):
                productos.append(v.get('producto', 'Desconocido'))
        
        # Datos mensuales
        por_mes = defaultdict(lambda: {'ingresos': 0, 'ventas': 0})
        for r in self.datos:
            mes = r.get('fecha', '2000-01')[:7]  # YYYY-MM
            por_mes[mes]['ingresos'] += r.get('total_dia', 0)
            por_mes[mes]['ventas'] += r.get('total_ventas', 0)
        
        return {
            # Promedios
            'promedio_dia': np.mean(ingresos),
            'promedio_mes': np.mean([m['ingresos'] for m in por_mes.values()]),
            
            # Media (igual que promedio)
            'media': np.mean(ingresos),
            
            # Mediana
            'mediana': np.median(ingresos),
            
            # Moda (producto más vendido)
            'moda_producto': Counter(productos).most_common(1)[0] if productos else ('N/A', 0),
            
            # Percentiles
            'percentil_25': np.percentile(ingresos, 25),
            'percentil_50': np.percentile(ingresos, 50),
            'percentil_75': np.percentile(ingresos, 75),
            
            # Otros
            'total': sum(ingresos),
            'mejor_dia': max(ingresos) if ingresos else 0,
            'peor_dia': min(ingresos) if ingresos else 0,
            'desviacion': np.std(ingresos),
            'datos_mes': por_mes
        }
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas en texto"""
        stats = self.calcular_estadisticas()
        if not stats:
            print("\n⚠ No hay datos disponibles\n")
            return
        
        print(f"""
╔══════════════════════════════════════════════════════════╗
║              ESTADÍSTICAS FINANCIERAS                    ║
╚══════════════════════════════════════════════════════════╝

📊 MEDIDAS DE TENDENCIA CENTRAL
────────────────────────────────────────────────────────────
  Media (Promedio):      ${stats['media']:>12,.0f} COP
  Mediana:               ${stats['mediana']:>12,.0f} COP
  Moda (Producto):       {stats['moda_producto'][0][:25]:>25s}
                         ({stats['moda_producto'][1]} ventas)

📈 PERCENTILES
────────────────────────────────────────────────────────────
  25% (Q1):              ${stats['percentil_25']:>12,.0f} COP
  50% (Q2 - Mediana):    ${stats['percentil_50']:>12,.0f} COP
  75% (Q3):              ${stats['percentil_75']:>12,.0f} COP

💰 PROMEDIOS
────────────────────────────────────────────────────────────
  Promedio por día:      ${stats['promedio_dia']:>12,.0f} COP
  Promedio por mes:      ${stats['promedio_mes']:>12,.0f} COP

📉 DISPERSIÓN
────────────────────────────────────────────────────────────
  Desviación estándar:   ${stats['desviacion']:>12,.0f} COP
  
🎯 EXTREMOS
────────────────────────────────────────────────────────────
  Mejor día:             ${stats['mejor_dia']:>12,.0f} COP
  Peor día:              ${stats['peor_dia']:>12,.0f} COP
  Total periodo:         ${stats['total']:>12,.0f} COP

╚══════════════════════════════════════════════════════════╝
""")
    
    def graficar_todo(self):
        """Genera todas las gráficas en un dashboard compacto"""
        if not self.datos:
            print("No hay datos")
            return
        
        stats = self.calcular_estadisticas()
        fig = plt.figure(figsize=(14, 8))
        fig.suptitle('📊 DASHBOARD FINANCIERO', fontsize=16, fontweight='bold')
        
        # 1. Ventas diarias
        ax1 = plt.subplot(2, 3, 1)
        fechas = [d.get('fecha', '') for d in self.datos]
        ingresos = [d.get('total_dia', 0) for d in self.datos]
        ax1.plot(ingresos, marker='o', color='#4CAF50')
        ax1.set_title('💰 Ingresos Diarios')
        ax1.grid(True, alpha=0.3)
        
        # 2. Ingresos mensuales
        ax2 = plt.subplot(2, 3, 2)
        meses = sorted(stats['datos_mes'].keys())
        ingresos_mes = [stats['datos_mes'][m]['ingresos'] for m in meses]
        ax2.bar(range(len(meses)), ingresos_mes, color='#2196F3')
        ax2.set_title('📅 Ingresos Mensuales')
        ax2.set_xticks(range(len(meses)))
        ax2.set_xticklabels([m.split('-')[1] for m in meses])
        ax2.grid(True, alpha=0.3, axis='y')
        
        # 3. Box plot
        ax3 = plt.subplot(2, 3, 3)
        ax3.boxplot(ingresos, patch_artist=True,
                   boxprops=dict(facecolor='#FF9800', alpha=0.7))
        ax3.set_title('📦 Distribución (Percentiles)')
        ax3.set_ylabel('Ingresos')
        ax3.grid(True, alpha=0.3, axis='y')
        
        # 4. Producto más vendido
        ax4 = plt.subplot(2, 3, 4)
        todos_productos = []
        for r in self.datos:
            for v in r.get('ventas', []):
                todos_productos.append(v.get('producto', 'N/A'))
        
        top5 = Counter(todos_productos).most_common(5)
        productos = [p[0][:15] for p in top5]
        cantidades = [p[1] for p in top5]
        ax4.barh(productos, cantidades, color='#9C27B0')
        ax4.set_title('🏆 Top 5 Productos (Moda)')
        ax4.invert_yaxis()
        
        # 5. Estadísticas clave
        ax5 = plt.subplot(2, 3, 5)
        ax5.axis('off')
        texto = f"""
Estadísticas Clave

Media: ${stats['media']:,.0f}
Mediana: ${stats['mediana']:,.0f}

Percentil 25: ${stats['percentil_25']:,.0f}
Percentil 75: ${stats['percentil_75']:,.0f}

Promedio día: ${stats['promedio_dia']:,.0f}
Promedio mes: ${stats['promedio_mes']:,.0f}

Desv. Est: ${stats['desviacion']:,.0f}
        """
        ax5.text(0.1, 0.9, texto, transform=ax5.transAxes,
                fontsize=9, verticalalignment='top', fontfamily='monospace')
        
        # 6. Producto más vendido
        ax6 = plt.subplot(2, 3, 6)
        ax6.axis('off')
        moda_texto = f"""
Moda (Más Frecuente)

Producto:
{stats['moda_producto'][0][:20]}

Vendido:
{stats['moda_producto'][1]} veces

Es el producto con
mayor frecuencia de
ventas en el periodo
        """
        ax6.text(0.1, 0.9, moda_texto, transform=ax6.transAxes,
                fontsize=10, verticalalignment='top', fontfamily='monospace',
                color='#4CAF50', fontweight='bold')
        
        plt.tight_layout()
        return fig
    
    def exportar(self, nombre='dashboard.png'):
        """Exporta el dashboard"""
        fig = self.graficar_todo()
        if fig:
            fig.savefig(nombre, dpi=200, bbox_inches='tight', facecolor='#1e1e1e')
            plt.close(fig)
            print(f"✓ Exportado: {nombre}")


def main():
    print("\n" + "="*60)
    print(" "*15 + "📊 ANÁLISIS FINANCIERO")
    print("="*60)
    
    analizador = AnalizadorFinanciero()
    
    if not analizador.datos:
        print("\n⚠ No hay reportes en 'reportes/'\n")
        return
    
    print(f"\n✓ {len(analizador.datos)} reportes cargados")
    
    while True:
        print("\n" + "-"*60)
        print("1. 📊 Ver estadísticas")
        print("2. 📈 Ver gráficas")
        print("3. 💾 Exportar dashboard")
        print("4. 🔄 Recargar datos")
        print("5. ❌ Salir")
        print("-"*60)
        
        opcion = input("\n➤ Opción: ").strip()
        
        if opcion == "1":
            analizador.mostrar_estadisticas()
        
        elif opcion == "2":
            analizador.graficar_todo()
            plt.show()
        
        elif opcion == "3":
            nombre = input("Nombre (Enter=dashboard.png): ").strip()
            if not nombre:
                nombre = "dashboard.png"
            analizador.exportar(nombre)
        
        elif opcion == "4":
            analizador.cargar_datos()
            print(f"\n✓ {len(analizador.datos)} reportes cargados")
        
        elif opcion == "5":
            print("\n👋 Hasta luego!\n")
            break


if __name__ == "__main__":
    main()