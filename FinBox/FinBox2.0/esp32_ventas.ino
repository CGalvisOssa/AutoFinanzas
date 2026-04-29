#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <ArduinoJson.h>
#include <time.h>
#include <ESPAsyncWebServer.h>

#ifdef CLOSED
#undef CLOSED
#endif

#include <Keypad.h>

// Configuración de la pantalla OLED SH1106
#define i2c_Address 0x3c
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SH1106G display = Adafruit_SH1106G(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Configuración del teclado matricial 4x4
const byte ROWS = 4;
const byte COLS = 4;
char keys[ROWS][COLS] = {
  {'1','2','3','A'},
  {'4','5','6','B'},
  {'7','8','9','C'},
  {'*','0','#','D'}
};
byte rowPins[ROWS] = {13, 12, 14, 27};
byte colPins[COLS] = {26, 25, 33, 32};
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

// Configuración WiFi
const char* ssid     = "UTP";
const char* password = "tecnologica";

// Servidor web
AsyncWebServer server(80);

// Catálogo de productos
struct Producto {
  String codigo;
  String nombre;
  String descripcion;
};

Producto catalogo[] = {
  {"01", "Lapicero",           "Lapicero tinta azul/negra"},
  {"02", "Lapiz",              "Lapiz de grafito HB"},
  {"03", "Borrador",           "Borrador blanco o de nata"},
  {"04", "Sacapuntas",         "Sacapuntas metalico o plastico"},
  {"05", "Marcador",           "Marcador permanente o de pizarra"},
  {"06", "Cuaderno",           "Cuaderno universitario o pequeno"},
  {"07", "Carpeta",            "Carpeta plastica o de anillas"},
  {"08", "Hojas sueltas",      "Resma o paquete de hojas blancas"},
  {"09", "Papel cuadriculado", "Hojas cuadriculadas o rayadas"},
  {"10", "Cartulina",          "Cartulina blanca o de color"},
  {"11", "Impresion B/N",      "Impresion laser o inyeccion B/N"},
  {"12", "Impresion color",    "Impresion a color"},
  {"13", "Fotocopia",          "Copia en blanco y negro"},
  {"14", "Escaneo",            "Escaneo de documentos o fotos"},
  {"15", "Plastificado",       "Plastificado de hojas o carnets"},
  {"16", "Tijeras",            "Tijeras escolares o de oficina"},
  {"17", "Regla",              "Regla de 30 cm o flexible"},
  {"18", "Pegante",            "Pegante en barra o liquido"},
  {"19", "Cinta adhesiva",     "Cinta transparente o masking tape"},
  {"20", "Grapadora",          "Grapadora mediana o mini"}
};

const int NUM_PRODUCTOS = 20;

// ── CAMBIO PRINCIPAL: cantidad en vez de valor ──────────────
struct Venta {
  String codigo;
  String producto;
  String descripcion;
  int    cantidad;      // <-- antes era "valor" en pesos
  String timestamp;
};
// ────────────────────────────────────────────────────────────

Venta  ventas[100];
int    numVentas    = 0;
String menuActual   = "PRINCIPAL";
String inputBuffer  = "";
String codigoTemp   = "";
int    ventaScrollPos = 0;

// Zona horaria Colombia UTC-5
const char* ntpServer        = "pool.ntp.org";
const long  gmtOffset_sec    = -5 * 3600;
const int   daylightOffset_sec = 0;

// ═══════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);

  if (!display.begin(i2c_Address, true)) {
    Serial.println("Error al inicializar OLED SH1106");
    while (1);
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SH110X_WHITE);
  display.setCursor(0, 0);
  display.println("Iniciando sistema...");
  display.display();
  delay(1000);

  conectarWiFi();
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  configurarServidor();
  mostrarMenuPrincipal();
}

void loop() {
  char key = keypad.getKey();
  if (key) procesarTecla(key);
}

// ═══════════════════════════════════════════════════════════
//  WiFi
// ═══════════════════════════════════════════════════════════
void conectarWiFi() {
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("Conectando WiFi...");
  display.display();

  WiFi.begin(ssid, password);
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 20) {
    delay(500);
    intentos++;
  }

  display.clearDisplay();
  display.setCursor(0, 0);
  if (WiFi.status() == WL_CONNECTED) {
    display.println("WiFi OK!");
    display.println();
    display.print("IP: ");
    display.println(WiFi.localIP());
    Serial.println("WiFi conectado - IP: " + WiFi.localIP().toString());
  } else {
    display.println("WiFi ERROR");
    display.println("Modo offline");
  }
  display.display();
  delay(2000);
}

// ═══════════════════════════════════════════════════════════
//  Servidor HTTP
// ═══════════════════════════════════════════════════════════
void configurarServidor() {
  // Reporte completo del día
  server.on("/reporte", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "application/json", generarReporteJSON());
  });

  // Estado rápido
  server.on("/status", HTTP_GET, [](AsyncWebServerRequest *request) {
    String s = "{\"ventas\":" + String(numVentas) + ",\"status\":\"ok\"}";
    request->send(200, "application/json", s);
  });

  // Catálogo
  server.on("/catalogo", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "application/json", generarCatalogoJSON());
  });

  server.begin();
  Serial.println("Servidor HTTP iniciado");
}

// ═══════════════════════════════════════════════════════════
//  Lógica de menús
// ═══════════════════════════════════════════════════════════
void procesarTecla(char key) {
  if      (menuActual == "PRINCIPAL")        procesarMenuPrincipal(key);
  else if (menuActual == "REGISTRAR_CODIGO") procesarRegistroCodigo(key);
  else if (menuActual == "REGISTRAR_CANT")   procesarRegistroCantidad(key); // <-- renombrado
  else if (menuActual == "ELIMINAR_SCROLL")  procesarEliminarScroll(key);
  else if (menuActual == "ELIMINAR_NUMERO")  procesarEliminarNumero(key);
}

void procesarMenuPrincipal(char key) {
  if (key == 'A') {
    menuActual  = "REGISTRAR_CODIGO";
    inputBuffer = "";
    mostrarRegistroCodigo();
  } else if (key == 'B') {
    if (numVentas == 0) {
      mostrarMensajeTemporal("No hay ventas\npara eliminar");
      mostrarMenuPrincipal();
    } else {
      menuActual    = "ELIMINAR_SCROLL";
      ventaScrollPos = 0;
      mostrarEliminarScroll();
    }
  } else if (key == 'C') {
    enviarReporte();
  }
}

void procesarRegistroCodigo(char key) {
  if (key == '#') {
    if (inputBuffer.length() >= 1) {
      codigoTemp = inputBuffer;
      codigoTemp.toUpperCase();
      inputBuffer = "";
      menuActual  = "REGISTRAR_CANT";   // <-- antes REGISTRAR_VALOR
      mostrarRegistroCantidad();
    }
  } else if (key == '*') {
    if (inputBuffer.length() > 0) {
      inputBuffer.remove(inputBuffer.length() - 1);
      mostrarRegistroCodigo();
    }
  } else if (key == 'D') {
    menuActual  = "PRINCIPAL";
    inputBuffer = "";
    mostrarMenuPrincipal();
  } else if (key != 'B' && key != 'C') {
    if (inputBuffer.length() < 10) {
      inputBuffer += key;
      mostrarRegistroCodigo();
    }
  }
}

// ── CAMBIO: pedir CANTIDAD en lugar de valor ────────────────
void procesarRegistroCantidad(char key) {
  if (key == '#') {
    if (inputBuffer.length() > 0) {
      int cantidad = inputBuffer.toInt();
      if (cantidad < 1) cantidad = 1;        // mínimo 1 unidad
      registrarVenta(codigoTemp, cantidad);
      inputBuffer = "";
      menuActual  = "PRINCIPAL";
      mostrarMensajeVentaRegistrada(cantidad);
      delay(1500);
      mostrarMenuPrincipal();
    }
  } else if (key == '*') {
    if (inputBuffer.length() > 0) {
      inputBuffer.remove(inputBuffer.length() - 1);
      mostrarRegistroCantidad();
    }
  } else if (key == 'D') {
    menuActual  = "PRINCIPAL";
    inputBuffer = "";
    mostrarMenuPrincipal();
  } else if (key >= '0' && key <= '9') {
    if (inputBuffer.length() < 4) {   // máximo 9999 unidades
      inputBuffer += key;
      mostrarRegistroCantidad();
    }
  }
}
// ────────────────────────────────────────────────────────────

void procesarEliminarScroll(char key) {
  if (key == '#') {
    ventaScrollPos++;
    if (ventaScrollPos >= numVentas) ventaScrollPos = 0;
    mostrarEliminarScroll();
  } else if (key == '*') {
    ventaScrollPos--;
    if (ventaScrollPos < 0) ventaScrollPos = numVentas - 1;
    mostrarEliminarScroll();
  } else if (key == '0') {
    menuActual  = "ELIMINAR_NUMERO";
    inputBuffer = "";
    mostrarEliminarNumero();
  } else if (key == 'D') {
    menuActual = "PRINCIPAL";
    mostrarMenuPrincipal();
  }
}

void procesarEliminarNumero(char key) {
  if (key == '#') {
    if (inputBuffer.length() > 0) {
      int numVenta = inputBuffer.toInt();
      if (numVenta > 0 && numVenta <= numVentas) {
        eliminarVenta(numVenta - 1);
        mostrarMensajeTemporal("Venta eliminada\ncon exito!");
      } else {
        mostrarMensajeTemporal("Numero invalido");
      }
    }
    menuActual  = "PRINCIPAL";
    inputBuffer = "";
    delay(2000);
    mostrarMenuPrincipal();
  } else if (key == '*') {
    if (inputBuffer.length() > 0) {
      inputBuffer.remove(inputBuffer.length() - 1);
      mostrarEliminarNumero();
    }
  } else if (key == 'D') {
    menuActual  = "PRINCIPAL";
    inputBuffer = "";
    mostrarMenuPrincipal();
  } else if (key >= '0' && key <= '9') {
    if (inputBuffer.length() < 3) {
      inputBuffer += key;
      mostrarEliminarNumero();
    }
  }
}

// ═══════════════════════════════════════════════════════════
//  Operaciones de ventas
// ═══════════════════════════════════════════════════════════
void registrarVenta(String codigo, int cantidad) {
  if (numVentas < 100) {
    ventas[numVentas].codigo      = codigo;
    ventas[numVentas].producto    = buscarProducto(codigo);
    ventas[numVentas].descripcion = buscarDescripcion(codigo);
    ventas[numVentas].cantidad    = cantidad;   // <-- cantidad, no valor
    ventas[numVentas].timestamp   = obtenerTimestamp();
    numVentas++;
    Serial.println("Venta " + String(numVentas) + ": ["
      + codigo + "] " + ventas[numVentas-1].producto
      + " x" + String(cantidad) + " uds.");
  }
}

void eliminarVenta(int indice) {
  String p = ventas[indice].producto;
  for (int i = indice; i < numVentas - 1; i++) ventas[i] = ventas[i + 1];
  numVentas--;
  Serial.println("Venta eliminada: " + p);
}

// ═══════════════════════════════════════════════════════════
//  JSON
// ═══════════════════════════════════════════════════════════
String generarReporteJSON() {
  DynamicJsonDocument doc(8192);

  doc["fecha"]        = obtenerFecha();
  doc["total_ventas"] = numVentas;

  int totalUnidades = 0;
  JsonArray arr = doc.createNestedArray("ventas");

  for (int i = 0; i < numVentas; i++) {
    JsonObject v = arr.createNestedObject();
    v["numero"]      = i + 1;
    v["codigo"]      = ventas[i].codigo;
    v["producto"]    = ventas[i].producto;
    v["descripcion"] = ventas[i].descripcion;
    v["cantidad"]    = ventas[i].cantidad;    // <-- campo renombrado
    v["timestamp"]   = ventas[i].timestamp;
    totalUnidades   += ventas[i].cantidad;
  }

  doc["total_unidades"] = totalUnidades;      // <-- resumen útil

  String output;
  serializeJson(doc, output);
  return output;
}

String generarCatalogoJSON() {
  DynamicJsonDocument doc(4096);
  JsonArray arr = doc.createNestedArray("productos");
  for (int i = 0; i < NUM_PRODUCTOS; i++) {
    JsonObject p  = arr.createNestedObject();
    p["codigo"]      = catalogo[i].codigo;
    p["nombre"]      = catalogo[i].nombre;
    p["descripcion"] = catalogo[i].descripcion;
  }
  String output;
  serializeJson(doc, output);
  return output;
}

// ═══════════════════════════════════════════════════════════
//  Helpers de tiempo
// ═══════════════════════════════════════════════════════════
String obtenerTimestamp() {
  struct tm t;
  if (!getLocalTime(&t)) return "N/A";
  char buf[30];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &t);
  return String(buf);
}

String obtenerFecha() {
  struct tm t;
  if (!getLocalTime(&t)) return "0000-00-00";
  char buf[15];
  strftime(buf, sizeof(buf), "%Y-%m-%d", &t);
  return String(buf);
}

// ═══════════════════════════════════════════════════════════
//  Reporte por pantalla
// ═══════════════════════════════════════════════════════════
void enviarReporte() {
  if (WiFi.status() != WL_CONNECTED) {
    mostrarMensajeTemporal("WiFi desconectado\nNo se puede enviar");
    delay(2000);
    mostrarMenuPrincipal();
    return;
  }

  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 5);
  display.println("Reporte disponible:");
  display.println();
  display.print("http://");
  display.println(WiFi.localIP());
  display.println("/reporte");
  display.println();
  display.print("Ventas: ");
  display.println(numVentas);
  display.display();

  Serial.println("=== REPORTE LISTO ===");
  Serial.println("URL: http://" + WiFi.localIP().toString() + "/reporte");
  Serial.println(generarReporteJSON());

  delay(4000);
  mostrarMenuPrincipal();
}

// ═══════════════════════════════════════════════════════════
//  Pantalla - menús
// ═══════════════════════════════════════════════════════════
void mostrarMenuPrincipal() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(12, 2);
  display.println("MENU PRINCIPAL");
  display.drawLine(0, 12, 128, 12, SH110X_WHITE);
  display.setCursor(5, 20);  display.println("A: Registrar venta");
  display.setCursor(5, 32);  display.println("B: Eliminar venta");
  display.setCursor(5, 44);  display.println("C: Ver reporte URL");
  display.drawLine(0, 54, 128, 54, SH110X_WHITE);
  display.setCursor(5, 57);
  display.print("Ventas hoy: ");
  display.println(numVentas);
  display.display();
}

void mostrarRegistroCodigo() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(5, 2);
  display.println("REGISTRAR VENTA");
  display.drawLine(0, 12, 128, 12, SH110X_WHITE);
  display.setCursor(5, 18);
  display.println("Codigo producto:");
  display.setTextSize(2);
  display.setCursor(20, 35);
  display.print(inputBuffer);
  display.print("_");
  display.setTextSize(1);
  display.setCursor(5, 55);
  display.println("#=OK *=Borrar D=Salir");
  display.display();
}

// ── CAMBIO: pantalla pide CANTIDAD ─────────────────────────
void mostrarRegistroCantidad() {
  String producto = buscarProducto(codigoTemp);

  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(5, 2);
  display.println("REGISTRAR VENTA");
  display.drawLine(0, 12, 128, 12, SH110X_WHITE);

  // Mostrar qué producto se seleccionó
  display.setCursor(5, 16);
  display.print("[");
  display.print(codigoTemp);
  display.print("] ");
  display.println(producto.substring(0, 12));

  // Pedir cantidad
  display.setCursor(5, 30);
  display.println("Cantidad de unidades:");

  display.setCursor(10, 42);
  display.setTextSize(2);
  display.print(inputBuffer.length() > 0 ? inputBuffer : "0");
  display.print("_");

  display.setTextSize(1);
  display.setCursor(5, 55);
  display.println("#=OK *=Borrar D=Salir");
  display.display();
}
// ────────────────────────────────────────────────────────────

void mostrarEliminarScroll() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(10, 2);
  display.println("ELIMINAR VENTA");
  display.drawLine(0, 12, 128, 12, SH110X_WHITE);
  display.setCursor(5, 18);
  display.println("Ventas del dia:");
  display.setCursor(5, 30);
  display.print(ventaScrollPos + 1);
  display.print(". [");
  display.print(ventas[ventaScrollPos].codigo);
  display.print("] ");
  display.println(ventas[ventaScrollPos].producto.substring(0, 8));
  display.setCursor(5, 40);
  display.print("Cant: x");
  display.println(ventas[ventaScrollPos].cantidad);   // <-- muestra cantidad
  display.drawLine(0, 51, 128, 51, SH110X_WHITE);
  display.setCursor(5, 54);
  display.println("*=Ant #=Sig 0=Elim");
  display.display();
}

void mostrarEliminarNumero() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(10, 2);
  display.println("ELIMINAR VENTA");
  display.drawLine(0, 12, 128, 12, SH110X_WHITE);
  display.setCursor(5, 22);
  display.println("Numero de venta");
  display.setCursor(5, 32);
  display.println("a eliminar:");
  display.setTextSize(2);
  display.setCursor(50, 42);
  display.print(inputBuffer);
  display.print("_");
  display.setTextSize(1);
  display.setCursor(5, 55);
  display.println("#=OK *=Borrar D=Salir");
  display.display();
}

// ── CAMBIO: confirmación muestra cantidad ──────────────────
void mostrarMensajeVentaRegistrada(int cantidad) {
  String producto = buscarProducto(codigoTemp);
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(15, 5);
  display.println("VENTA REGISTRADA");
  display.drawLine(0, 15, 128, 15, SH110X_WHITE);
  display.setCursor(5, 22);
  display.print("[");
  display.print(codigoTemp);
  display.print("] ");
  display.println(producto.substring(0, 12));
  display.setCursor(5, 36);
  display.print("Cantidad: x");
  display.println(cantidad);
  display.setCursor(5, 50);
  display.print("Total hoy: ");
  display.print(numVentas);
  display.println(" ventas");
  display.display();
}
// ────────────────────────────────────────────────────────────

void mostrarMensajeTemporal(const char* mensaje) {
  display.clearDisplay();
  display.setTextSize(1);
  int y = 25;
  String msg = String(mensaje);
  int start = 0, newlinePos = msg.indexOf('\n');
  while (newlinePos != -1) {
    String linea = msg.substring(start, newlinePos);
    int x = (128 - (linea.length() * 6)) / 2;
    display.setCursor(x, y);
    display.println(linea);
    y += 12;
    start = newlinePos + 1;
    newlinePos = msg.indexOf('\n', start);
  }
  if (start < msg.length()) {
    String linea = msg.substring(start);
    int x = (128 - (linea.length() * 6)) / 2;
    display.setCursor(x, y);
    display.println(linea);
  }
  display.display();
}

// ═══════════════════════════════════════════════════════════
//  Helpers de catálogo
// ═══════════════════════════════════════════════════════════
String buscarProducto(String codigo) {
  codigo.toUpperCase();
  for (int i = 0; i < NUM_PRODUCTOS; i++)
    if (catalogo[i].codigo == codigo) return catalogo[i].nombre;
  return "Desconocido";
}

String buscarDescripcion(String codigo) {
  codigo.toUpperCase();
  for (int i = 0; i < NUM_PRODUCTOS; i++)
    if (catalogo[i].codigo == codigo) return catalogo[i].descripcion;
  return "";
}
