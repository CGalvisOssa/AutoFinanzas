import os
import json
from datetime import datetime
from openai import OpenAI

class ChatFinanciero:
    def __init__(self, api_key=None, carpeta_reportes="reportes"):
        """
        Inicializa el chat financiero con OpenAI
        
        Args:
            api_key: API key de OpenAI (si no se proporciona, busca en variable de entorno)
            carpeta_reportes: Carpeta donde están los reportes JSON
        """
        self.carpeta_reportes = carpeta_reportes
        
        # Configurar API key
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            # Buscar en variable de entorno
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("No se encontró API key de OpenAI. Configúrala con set_api_key() o variable de entorno OPENAI_API_KEY")
            self.client = OpenAI(api_key=api_key)
        
        self.historial_conversacion = []
        print("✓ Chat con OpenAI inicializado")
    
    def set_api_key(self, api_key):
        """Configura la API key de OpenAI"""
        self.client = OpenAI(api_key=api_key)
        print("✓ API key configurada")
    
    def cargar_reportes(self):
        """Carga todos los reportes JSON disponibles"""
        if not os.path.exists(self.carpeta_reportes):
            return []
        
        reportes = []
        archivos = [f for f in os.listdir(self.carpeta_reportes) if f.endswith('.json')]
        
        for archivo in archivos:
            try:
                ruta = os.path.join(self.carpeta_reportes, archivo)
                with open(ruta, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    reportes.append(datos)
            except Exception as e:
                print(f"⚠ Error al cargar {archivo}: {e}")
        
        return reportes
    
    def generar_contexto_rag(self):
        """Genera el contexto RAG con todos los reportes disponibles"""
        reportes = self.cargar_reportes()
        
        if not reportes:
            return "No hay reportes de ventas disponibles actualmente."
        
        contexto = "=== DATOS DE VENTAS DISPONIBLES ===\n\n"
        
        for i, reporte in enumerate(reportes, 1):
            fecha = reporte.get('fecha', 'N/A')
            total_ventas = reporte.get('total_ventas', 0)
            total_dia = reporte.get('total_dia', 0)
            
            contexto += f"📅 Reporte {i} - Fecha: {fecha}\n"
            contexto += f"   Total de ventas: {total_ventas}\n"
            contexto += f"   Total recaudado: ${total_dia:,} COP\n"
            contexto += f"   Detalle de ventas:\n"
            
            for venta in reporte.get('ventas', []):
                codigo = venta.get('codigo', 'N/A')
                producto = venta.get('producto', 'N/A')
                descripcion = venta.get('descripcion', '')
                valor = venta.get('valor', 0)
                timestamp = venta.get('timestamp', 'N/A')
                
                contexto += f"     - [{codigo}] {producto}: ${valor:,} COP ({timestamp})\n"
            
            contexto += "\n"
        
        return contexto
    
    def calcular_estadisticas(self):
        """Calcula estadísticas generales de todos los reportes"""
        reportes = self.cargar_reportes()
        
        if not reportes:
            return None
        
        total_ventas = 0
        total_dinero = 0
        productos_vendidos = {}
        fechas = []
        
        for reporte in reportes:
            total_ventas += reporte.get('total_ventas', 0)
            total_dinero += reporte.get('total_dia', 0)
            fechas.append(reporte.get('fecha', 'N/A'))
            
            for venta in reporte.get('ventas', []):
                producto = venta.get('producto', 'Desconocido')
                valor = venta.get('valor', 0)
                
                if producto not in productos_vendidos:
                    productos_vendidos[producto] = {'cantidad': 0, 'total': 0}
                
                productos_vendidos[producto]['cantidad'] += 1
                productos_vendidos[producto]['total'] += valor
        
        # Producto más vendido
        producto_top = max(productos_vendidos.items(), 
                          key=lambda x: x[1]['cantidad']) if productos_vendidos else None
        
        estadisticas = {
            'total_ventas': total_ventas,
            'total_dinero': total_dinero,
            'promedio_por_venta': total_dinero / total_ventas if total_ventas > 0 else 0,
            'productos_diferentes': len(productos_vendidos),
            'producto_mas_vendido': producto_top[0] if producto_top else 'N/A',
            'cantidad_producto_top': producto_top[1]['cantidad'] if producto_top else 0,
            'fechas_registradas': len(fechas),
            'rango_fechas': f"{min(fechas)} a {max(fechas)}" if fechas else 'N/A'
        }
        
        return estadisticas
    
    def generar_contexto_estadisticas(self):
        """Genera contexto con estadísticas resumidas"""
        stats = self.calcular_estadisticas()
        
        if not stats:
            return ""
        
        contexto = "\n=== ESTADÍSTICAS GENERALES ===\n\n"
        contexto += f"📊 Total de ventas registradas: {stats['total_ventas']}\n"
        contexto += f"💰 Total recaudado: ${stats['total_dinero']:,} COP\n"
        contexto += f"📈 Promedio por venta: ${stats['promedio_por_venta']:,.2f} COP\n"
        contexto += f"🏆 Producto más vendido: {stats['producto_mas_vendido']} ({stats['cantidad_producto_top']} ventas)\n"
        contexto += f"📦 Productos diferentes: {stats['productos_diferentes']}\n"
        contexto += f"📅 Periodo: {stats['rango_fechas']}\n"
        
        return contexto
    
    def chat(self, pregunta_usuario, incluir_estadisticas=True):
        """
        Realiza una consulta al modelo de OpenAI con contexto RAG
        
        Args:
            pregunta_usuario: Pregunta del usuario
            incluir_estadisticas: Si incluir estadísticas en el contexto
        
        Returns:
            Respuesta del modelo
        """
        # Generar contexto RAG
        contexto_reportes = self.generar_contexto_rag()
        contexto_stats = self.generar_contexto_estadisticas() if incluir_estadisticas else ""
        
        # Sistema prompt con contexto
        system_prompt = f"""Eres un asistente financiero experto especializado en análisis de ventas de papelerías.

Tienes acceso a los siguientes datos de ventas:

{contexto_reportes}
{contexto_stats}

Tu objetivo es:
1. Analizar los datos de ventas proporcionados
2. Responder preguntas sobre tendencias, productos más vendidos, estadísticas, etc.
3. Dar recomendaciones basadas en los datos
4. Ser preciso con los números y fechas
5. Usar formato claro con emojis cuando sea apropiado

Si te preguntan algo que no esté en los datos, indícalo claramente.
Siempre menciona los valores en pesos colombianos (COP).
"""
        
        # Agregar mensaje del usuario al historial
        self.historial_conversacion.append({
            "role": "user",
            "content": pregunta_usuario
        })
        
        try:
            # Llamar a OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Puedes cambiar a "gpt-4" si tienes acceso
                messages=[
                    {"role": "system", "content": system_prompt}
                ] + self.historial_conversacion,
                temperature=0.7,
                max_tokens=1500
            )
            
            respuesta = response.choices[0].message.content
            
            # Agregar respuesta al historial
            self.historial_conversacion.append({
                "role": "assistant",
                "content": respuesta
            })
            
            return respuesta
        
        except Exception as e:
            return f"❌ Error al comunicarse con OpenAI: {str(e)}"
    
    def limpiar_historial(self):
        """Limpia el historial de conversación"""
        self.historial_conversacion = []
        print("✓ Historial de conversación limpiado")
    
    def exportar_conversacion(self, nombre_archivo=None):
        """Exporta la conversación a un archivo JSON"""
        if not nombre_archivo:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"conversacion_{timestamp}.json"
        
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            json.dump(self.historial_conversacion, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Conversación exportada a: {nombre_archivo}")


def menu_chat():
    """Menú interactivo para el chat financiero"""
    
    # Verificar si existe API key
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("\n" + "="*60)
        print("CONFIGURACIÓN DE API KEY DE OPENAI")
        print("="*60)
        print("\nNo se encontró la API key de OpenAI.")
        print("\nOpciones:")
        print("1. Ingresarla ahora manualmente")
        print("2. Configurar variable de entorno OPENAI_API_KEY")
        print("\nPara obtener tu API key:")
        print("→ Ve a https://platform.openai.com/api-keys")
        print("→ Crea una nueva API key")
        print("→ Cópiala (solo se muestra una vez)")
        
        opcion = input("\n¿Qué deseas hacer? (1/2): ").strip()
        
        if opcion == "1":
            api_key = input("\nIngresa tu API key de OpenAI: ").strip()
            if not api_key:
                print("❌ API key no proporcionada")
                return
        else:
            print("\n💡 Para configurar la variable de entorno:")
            print("   Windows: set OPENAI_API_KEY=tu-api-key")
            print("   Linux/Mac: export OPENAI_API_KEY=tu-api-key")
            return
    
    try:
        chat = ChatFinanciero(api_key=api_key)
    except Exception as e:
        print(f"\n❌ Error al inicializar chat: {e}")
        return
    
    print("\n" + "💬 "*20)
    print(" "*15 + "CHAT FINANCIERO CON IA")
    print("💬 "*20)
    print("\n✨ Puedes hacer preguntas como:")
    print("   - ¿Cuál fue el producto más vendido?")
    print("   - ¿Cuánto se vendió el día X?")
    print("   - ¿Qué tendencias ves en las ventas?")
    print("   - Dame recomendaciones para aumentar ventas")
    print("   - Analiza las ventas por categoría")
    print("\nEscribe 'salir' para terminar, 'limpiar' para nuevo chat")
    print("="*60 + "\n")
    
    while True:
        pregunta = input("🤔 Tú: ").strip()
        
        if not pregunta:
            continue
        
        if pregunta.lower() in ['salir', 'exit', 'quit']:
            print("\n👋 ¡Hasta luego!\n")
            
            # Preguntar si quiere exportar la conversación
            exportar = input("¿Deseas exportar esta conversación? (s/n): ").strip().lower()
            if exportar == 's':
                chat.exportar_conversacion()
            break
        
        if pregunta.lower() in ['limpiar', 'clear', 'nuevo']:
            chat.limpiar_historial()
            print("\n✨ Historial limpiado. Comenzamos una nueva conversación.\n")
            continue
        
        if pregunta.lower() in ['stats', 'estadisticas', 'resumen']:
            stats = chat.calcular_estadisticas()
            if stats:
                print("\n" + "📊 "*20)
                print(chat.generar_contexto_estadisticas())
                print("📊 "*20 + "\n")
            else:
                print("\n⚠ No hay datos disponibles\n")
            continue
        
        print("\n🤖 Asistente: ", end="", flush=True)
        respuesta = chat.chat(pregunta)
        print(respuesta + "\n")


if __name__ == "__main__":
    menu_chat()