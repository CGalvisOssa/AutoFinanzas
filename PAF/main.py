import requests
import json
import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import pickle

# Configuración
ESP32_IP = "192.168.1.100"  # Cambiar por la IP de tu ESP32
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class SistemaFinanciero:
    def __init__(self):
        self.carpeta_reportes = "reportes"
        self.carpeta_drive = None
        self.service = None
        self.esp32_ip = ESP32_IP
        
        # Crear carpeta de reportes si no existe
        if not os.path.exists(self.carpeta_reportes):
            os.makedirs(self.carpeta_reportes)
            print(f"✓ Carpeta '{self.carpeta_reportes}' creada")
    
    def autenticar_google_drive(self):
        """Autentica con Google Drive"""
        creds = None
        
        # Token guardado de sesiones anteriores
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        # Si no hay credenciales válidas, solicitar login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    print("\n✗ ERROR: No se encontró 'credentials.json'")
                    print("Para configurar Google Drive:")
                    print("1. Ve a https://console.cloud.google.com/")
                    print("2. Crea un proyecto nuevo")
                    print("3. Habilita Google Drive API")
                    print("4. Crea credenciales OAuth 2.0")
                    print("5. Descarga el archivo JSON como 'credentials.json'")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Guardar credenciales para la próxima vez
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('drive', 'v3', credentials=creds)
        print("✓ Autenticado con Google Drive")
        
        # Crear carpeta en Drive si no existe
        self.crear_carpeta_drive()
        return True
    
    def crear_carpeta_drive(self):
        """Crea carpeta 'Reportes Financieros' en Drive"""
        query = "name='Reportes Financieros' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get('files', [])
        
        if folders:
            self.carpeta_drive = folders[0]['id']
            print(f"✓ Carpeta existente encontrada: {folders[0]['name']}")
        else:
            file_metadata = {
                'name': 'Reportes Financieros',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(body=file_metadata, fields='id').execute()
            self.carpeta_drive = folder.get('id')
            print("✓ Carpeta 'Reportes Financieros' creada en Drive")
    
    def obtener_reporte_esp32(self):
        """Obtiene el reporte del ESP32 vía HTTP"""
        try:
            print(f"Conectando a ESP32 en {self.esp32_ip}...")
            url = f"http://{self.esp32_ip}/reporte"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                datos = response.json()
                print("✓ Reporte obtenido del ESP32")
                return datos
            else:
                print(f"✗ Error HTTP: {response.status_code}")
                return None
        except requests.exceptions.ConnectionError:
            print(f"✗ Error: No se pudo conectar al ESP32 en {self.esp32_ip}")
            print("  Verifica que:")
            print("  - El ESP32 esté encendido")
            print("  - Esté conectado a la misma red WiFi")
            print("  - La IP sea correcta")
            return None
        except requests.exceptions.Timeout:
            print(f"✗ Error: Timeout al conectar con {self.esp32_ip}")
            return None
        except Exception as e:
            print(f"✗ Error de conexión: {e}")
            return None
    
    def guardar_reporte_local(self, datos):
        """Guarda el reporte en archivo JSON local"""
        if not datos:
            return None
        
        fecha = datos.get('fecha', datetime.now().strftime('%Y-%m-%d'))
        hora = datetime.now().strftime('%H%M%S')
        nombre_archivo = f"reporte_{fecha}_{hora}.json"
        ruta_completa = os.path.join(self.carpeta_reportes, nombre_archivo)
        
        with open(ruta_completa, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Reporte guardado localmente: {nombre_archivo}")
        return ruta_completa
    
    def subir_a_drive(self, ruta_archivo):
        """Sube el archivo a Google Drive"""
        if not self.service:
            print("✗ No hay conexión con Google Drive")
            return False
        
        try:
            nombre_archivo = os.path.basename(ruta_archivo)
            
            file_metadata = {
                'name': nombre_archivo,
                'parents': [self.carpeta_drive]
            }
            
            media = MediaFileUpload(ruta_archivo, mimetype='application/json')
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            print(f"✓ Archivo subido a Google Drive (ID: {file.get('id')})")
            return True
        
        except Exception as e:
            print(f"✗ Error al subir a Drive: {e}")
            return False
    
    def generar_resumen(self, datos):
        """Genera resumen del reporte"""
        if not datos:
            return
        
        print("\n" + "="*60)
        print(" "*20 + "RESUMEN DEL REPORTE")
        print("="*60)
        print(f"📅 Fecha: {datos.get('fecha', 'N/A')}")
        print(f"📊 Total de ventas: {datos.get('total_ventas', 0)}")
        print(f"💰 Total del día: ${datos.get('total_dia', 0):,} COP")
        
        if datos.get('ventas'):
            print("\n" + "-"*60)
            print("Ventas detalladas:")
            print("-"*60)
            
            for venta in datos.get('ventas', []):
                timestamp = venta.get('timestamp', 'N/A')
                print(f"  {venta['numero']}. {venta['producto']:15s} ${venta['valor']:>8,} COP  [{timestamp}]")
        else:
            print("\nNo hay ventas registradas.")
        
        print("="*60 + "\n")
    
    def procesar_reporte_completo(self):
        """Proceso completo: obtener, guardar local y subir a Drive"""
        print("\n" + "🚀 "*20)
        print("INICIANDO PROCESO DE RECEPCIÓN DE REPORTE")
        print("🚀 "*20 + "\n")
        
        # 1. Obtener reporte del ESP32
        datos = self.obtener_reporte_esp32()
        if not datos:
            print("\n✗ No se pudo obtener el reporte del ESP32")
            print("El proceso ha finalizado sin éxito.\n")
            return False
        
        # 2. Mostrar resumen
        self.generar_resumen(datos)
        
        # 3. Guardar localmente
        ruta_archivo = self.guardar_reporte_local(datos)
        if not ruta_archivo:
            print("✗ Error al guardar reporte local")
            return False
        
        # 4. Subir a Google Drive
        if self.service:
            self.subir_a_drive(ruta_archivo)
        else:
            print("⚠ Google Drive no configurado, solo guardado local")
        
        print("\n" + "✅ "*20)
        print("PROCESO COMPLETADO EXITOSAMENTE")
        print("✅ "*20 + "\n")
        return True
    
    def ver_reportes_locales(self):
        """Muestra los reportes guardados localmente"""
        if not os.path.exists(self.carpeta_reportes):
            print("\n⚠ No hay carpeta de reportes")
            return
        
        archivos = sorted([f for f in os.listdir(self.carpeta_reportes) if f.endswith('.json')])
        
        if not archivos:
            print("\n⚠ No hay reportes guardados")
            return
        
        print("\n" + "="*60)
        print(" "*20 + "REPORTES LOCALES")
        print("="*60)
        
        for i, archivo in enumerate(archivos, 1):
            ruta = os.path.join(self.carpeta_reportes, archivo)
            tamaño = os.path.getsize(ruta)
            fecha_mod = datetime.fromtimestamp(os.path.getmtime(ruta))
            
            print(f"{i:3d}. {archivo:40s} {tamaño:>6,} bytes  {fecha_mod.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("="*60 + "\n")
        
        # Opción para ver el contenido de un reporte
        try:
            opcion = input("¿Ver contenido de algún reporte? (número o Enter para salir): ").strip()
            if opcion.isdigit():
                idx = int(opcion) - 1
                if 0 <= idx < len(archivos):
                    self.ver_contenido_reporte(os.path.join(self.carpeta_reportes, archivos[idx]))
        except:
            pass
    
    def ver_contenido_reporte(self, ruta_archivo):
        """Muestra el contenido de un reporte"""
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            self.generar_resumen(datos)
        except Exception as e:
            print(f"✗ Error al leer el archivo: {e}")
    
    def configurar_ip(self, nueva_ip):
        """Configura nueva IP del ESP32"""
        self.esp32_ip = nueva_ip
        print(f"✓ IP del ESP32 configurada: {nueva_ip}")


def menu_principal():
    """Menú interactivo"""
    sistema = SistemaFinanciero()
    
    print("\n" + "="*60)
    print(" "*15 + "SISTEMA DE GESTIÓN FINANCIERA")
    print(" "*20 + "Versión 1.0 - 2025")
    print("="*60)
    
    while True:
        print("\n" + "─"*60)
        print("MENÚ PRINCIPAL")
        print("─"*60)
        print("1. Configurar Google Drive")
        print(f"2. Obtener reporte del ESP32 [{sistema.esp32_ip}]")
        print("3. Ver reportes locales")
        print("4. Cambiar IP del ESP32")
        print("5. Verificar conexión con ESP32")
        print("6. Salir")
        print("─"*60)
        
        opcion = input("\n➤ Seleccione una opción: ").strip()
        
        if opcion == "1":
            print("\n" + "📁 "*20)
            print("CONFIGURACIÓN DE GOOGLE DRIVE")
            print("📁 "*20 + "\n")
            sistema.autenticar_google_drive()
        
        elif opcion == "2":
            # Usar la IP configurada directamente
            sistema.procesar_reporte_completo()
        
        elif opcion == "3":
            sistema.ver_reportes_locales()
        
        elif opcion == "4":
            nueva_ip = input("\n➤ Nueva IP del ESP32: ").strip()
            if nueva_ip:
                sistema.configurar_ip(nueva_ip)
            else:
                print("⚠ IP no cambiada")
        
        elif opcion == "5":
            print("\n🔍 Verificando conexión con ESP32...\n")
            
            try:
                url = f"http://{sistema.esp32_ip}/status"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    datos = response.json()
                    print("\n✓ ESP32 conectado y funcionando")
                    print(f"  - IP: {sistema.esp32_ip}")
                    print(f"  - Ventas registradas: {datos.get('ventas', 0)}")
                    print(f"  - Estado: {datos.get('status', 'N/A')}")
                else:
                    print(f"\n⚠ ESP32 responde pero con error: {response.status_code}")
            except:
                print(f"\n✗ No se pudo conectar al ESP32 en {sistema.esp32_ip}")
                print("  Verifica que el ESP32 esté encendido y en la misma red")
        
        elif opcion == "6":
            print("\n👋 ¡Hasta luego!\n")
            break
        
        else:
            print("\n⚠ Opción inválida, intente nuevamente")


if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n👋 Programa interrumpido por el usuario\n")
    except Exception as e:
        print(f"\n✗ Error inesperado: {e}\n")