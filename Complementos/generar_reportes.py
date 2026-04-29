import json
import os
from datetime import datetime, timedelta
import random

class GeneradorReportes:
    def __init__(self):
        self.productos = [
            {"codigo": "01", "producto": "Lapicero", "descripcion": "Lapicero tinta azul/negra", "valor": 1500},
            {"codigo": "02", "producto": "Lapiz", "descripcion": "Lapiz de grafito HB", "valor": 800},
            {"codigo": "03", "producto": "Borrador", "descripcion": "Borrador blanco o de nata", "valor": 600},
            {"codigo": "04", "producto": "Sacapuntas", "descripcion": "Sacapuntas metalico o plastico", "valor": 1200},
            {"codigo": "05", "producto": "Marcador", "descripcion": "Marcador permanente o de pizarra", "valor": 2500},
            {"codigo": "06", "producto": "Cuaderno", "descripcion": "Cuaderno universitario o pequeno", "valor": 4500},
            {"codigo": "07", "producto": "Carpeta", "descripcion": "Carpeta plastica o de anillas", "valor": 3800},
            {"codigo": "08", "producto": "Hojas sueltas", "descripcion": "Resma o paquete de hojas blancas", "valor": 2800},
            {"codigo": "09", "producto": "Papel cuadriculado", "descripcion": "Hojas cuadriculadas o rayadas", "valor": 3200},
            {"codigo": "10", "producto": "Cartulina", "descripcion": "Cartulina blanca o de color", "valor": 800},
            {"codigo": "11", "producto": "Impresion B/N", "descripcion": "Impresion laser o inyeccion B/N", "valor": 300},
            {"codigo": "12", "producto": "Impresion color", "descripcion": "Impresion a color", "valor": 1500},
            {"codigo": "13", "producto": "Fotocopia", "descripcion": "Copia en blanco y negro", "valor": 200},
            {"codigo": "14", "producto": "Escaneo", "descripcion": "Escaneo de documentos o fotos", "valor": 500},
            {"codigo": "15", "producto": "Plastificado", "descripcion": "Plastificado de hojas o carnets", "valor": 2000},
            {"codigo": "16", "producto": "Tijeras", "descripcion": "Tijeras escolares o de oficina", "valor": 3500},
            {"codigo": "17", "producto": "Regla", "descripcion": "Regla de 30 cm o flexible", "valor": 1800},
            {"codigo": "18", "producto": "Pegante", "descripcion": "Pegante en barra o liquido", "valor": 2200},
            {"codigo": "19", "producto": "Cinta adhesiva", "descripcion": "Cinta transparente o masking tape", "valor": 1600},
            {"codigo": "20", "producto": "Grapadora", "descripcion": "Grapadora mediana o mini", "valor": 4200}
        ]

    def generar_reporte_dia(self, fecha):
        total_ventas = random.randint(1, 10)
        ventas = []
        total_dia = 0
        
        for i in range(total_ventas):
            producto = random.choice(self.productos)
            hora = random.randint(8, 20)
            minuto = random.randint(0, 59)
            timestamp = f"{fecha} {hora:02d}:{minuto:02d}:00"
            
            venta = {
                "numero": i + 1,
                "codigo": producto["codigo"],
                "producto": producto["producto"],
                "descripcion": producto["descripcion"],
                "valor": producto["valor"],
                "timestamp": timestamp
            }
            ventas.append(venta)
            total_dia += producto["valor"]
        
        return {
            "fecha": fecha,
            "total_ventas": total_ventas,
            "ventas": ventas,
            "total_dia": total_dia
        }

    def generar_mes(self, año, mes, carpeta="reportes"):
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)
        
        # Calcular días del mes
        if mes == 12:
            siguiente_mes = 1
            siguiente_año = año + 1
        else:
            siguiente_mes = mes + 1
            siguiente_año = año
        
        fecha_inicio = datetime(año, mes, 1)
        fecha_fin = datetime(siguiente_año, siguiente_mes, 1) - timedelta(days=1)
        total_dias = (fecha_fin - fecha_inicio).days + 1
        
        for dia in range(1, total_dias + 1):
            fecha = f"{año}-{mes:02d}-{dia:02d}"
            reporte = self.generar_reporte_dia(fecha)
            
            nombre_archivo = f"reporte_{fecha}_120000.json"
            with open(os.path.join(carpeta, nombre_archivo), 'w', encoding='utf-8') as f:
                json.dump(reporte, f, indent=2, ensure_ascii=False)
        
        print(f"Generados {total_dias} reportes para {mes:02d}/{año} en carpeta '{carpeta}'")

# Uso del programa
if __name__ == "__main__":
    generador = GeneradorReportes()
    generador.generar_mes(2024, 10)  # Genera reportes para octubre 2024