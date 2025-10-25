#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SH110X.h>
#include <Keypad.h>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include <time.h>

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
const char* ssid = "RepetidorFliaGalvis";          
const char* password = "Alba2002";   

// Servidor web
AsyncWebServer server(80);

// Estructura para almacenar ventas
struct Venta {
  String producto;
  int valor;
  String timestamp;
};

// Variables globales
Venta ventas[100];
int numVentas = 0;
String menuActual = "PRINCIPAL";
String inputBuffer = "";
String productoTemp = "";
int ventaScrollPos = 0;

// Configuración de zona horaria (Colombia UTC-5)
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = -5 * 3600;
const int daylightOffset_sec = 0;

void setup() {
  Serial.begin(115200);
  
  // Inicializar pantalla OLED SH1106
  if(!display.begin(i2c_Address, true)) {
    Serial.println("Error al inicializar OLED SH1106");
    while(1);
  }
  
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SH110X_WHITE);
  display.setCursor(0, 0);
  display.println("Iniciando sistema...");
  display.display();
  delay(1000);
  
  // Conectar a WiFi
  conectarWiFi();
  
  // Configurar hora
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  
  // Configurar servidor web
  configurarServidor();
  
  mostrarMenuPrincipal();
}

void loop() {
  char key = keypad.getKey();
  
  if (key) {
    procesarTecla(key);
  }
}

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

void configurarServidor() {
  // Endpoint para obtener el reporte del día
  server.on("/reporte", HTTP_GET, [](AsyncWebServerRequest *request){
    String json = generarReporteJSON();
    request->send(200, "application/json", json);
  });
  
  // Endpoint para verificar estado
  server.on("/status", HTTP_GET, [](AsyncWebServerRequest *request){
    String status = "{\"ventas\":" + String(numVentas) + ",\"status\":\"ok\"}";
    request->send(200, "application/json", status);
  });
  
  server.begin();
  Serial.println("Servidor HTTP iniciado");
}

void procesarTecla(char key) {
  if (menuActual == "PRINCIPAL") {
    procesarMenuPrincipal(key);
  } else if (menuActual == "REGISTRAR_PRODUCTO") {
    procesarRegistroProducto(key);
  } else if (menuActual == "REGISTRAR_VALOR") {
    procesarRegistroValor(key);
  } else if (menuActual == "ELIMINAR_SCROLL") {
    procesarEliminarScroll(key);
  } else if (menuActual == "ELIMINAR_NUMERO") {
    procesarEliminarNumero(key);
  }
}

void procesarMenuPrincipal(char key) {
  if (key == 'A') {
    menuActual = "REGISTRAR_PRODUCTO";
    inputBuffer = "";
    mostrarRegistroProducto();
  } else if (key == 'B') {
    if (numVentas == 0) {
      mostrarMensajeTemporal("No hay ventas\npara eliminar");
      mostrarMenuPrincipal();
    } else {
      menuActual = "ELIMINAR_SCROLL";
      ventaScrollPos = 0;
      mostrarEliminarScroll();
    }
  } else if (key == 'C') {
    enviarReporte();
  }
}

void procesarRegistroProducto(char key) {
  if (key == '#') {  // Confirmar
    if (inputBuffer.length() >= 2) {
      productoTemp = inputBuffer;
      inputBuffer = "";
      menuActual = "REGISTRAR_VALOR";
      mostrarRegistroValor();
    }
  } else if (key == '*') {  // Borrar último carácter
    if (inputBuffer.length() > 0) {
      inputBuffer.remove(inputBuffer.length() - 1);
      mostrarRegistroProducto();
    }
  } else if (key == 'D') {  // Cancelar
    menuActual = "PRINCIPAL";
    inputBuffer = "";
    mostrarMenuPrincipal();
  } else if (key != 'A' && key != 'B' && key != 'C') {
    if (inputBuffer.length() < 10) {
      inputBuffer += key;
      mostrarRegistroProducto();
    }
  }
}

void procesarRegistroValor(char key) {
  if (key == '#') {  // Confirmar
    if (inputBuffer.length() > 0) {
      int valor = inputBuffer.toInt();
      registrarVenta(productoTemp, valor);
      inputBuffer = "";
      menuActual = "PRINCIPAL";
      mostrarMensajeVentaRegistrada();
      delay(2000);
      mostrarMenuPrincipal();
    }
  } else if (key == '*') {  // Borrar último carácter
    if (inputBuffer.length() > 0) {
      inputBuffer.remove(inputBuffer.length() - 1);
      mostrarRegistroValor();
    }
  } else if (key == 'D') {  // Cancelar
    menuActual = "PRINCIPAL";
    inputBuffer = "";
    mostrarMenuPrincipal();
  } else if (key >= '0' && key <= '9') {
    if (inputBuffer.length() < 8) {
      inputBuffer += key;
      mostrarRegistroValor();
    }
  }
}

void procesarEliminarScroll(char key) {
  if (key == '#') {  // Siguiente venta (derecha)
    ventaScrollPos++;
    if (ventaScrollPos >= numVentas) ventaScrollPos = 0;  // Ciclar al inicio
    mostrarEliminarScroll();
  } else if (key == '*') {  // Venta anterior (izquierda)
    ventaScrollPos--;
    if (ventaScrollPos < 0) ventaScrollPos = numVentas - 1;  // Ciclar al final
    mostrarEliminarScroll();
  } else if (key == '0') {  // Confirmar selección para eliminar
    menuActual = "ELIMINAR_NUMERO";
    inputBuffer = "";
    mostrarEliminarNumero();
  } else if (key == 'D') {  // Cancelar
    menuActual = "PRINCIPAL";
    mostrarMenuPrincipal();
  }
}

void procesarEliminarNumero(char key) {
  if (key == '#') {  // Confirmar eliminación
    if (inputBuffer.length() > 0) {
      int numVenta = inputBuffer.toInt();
      if (numVenta > 0 && numVenta <= numVentas) {
        eliminarVenta(numVenta - 1);
        mostrarMensajeTemporal("Venta eliminada\ncon exito!");
      } else {
        mostrarMensajeTemporal("Numero invalido");
      }
    }
    menuActual = "PRINCIPAL";
    inputBuffer = "";
    delay(2000);
    mostrarMenuPrincipal();
  } else if (key == '*') {  // Borrar último carácter
    if (inputBuffer.length() > 0) {
      inputBuffer.remove(inputBuffer.length() - 1);
      mostrarEliminarNumero();
    }
  } else if (key == 'D') {  // Cancelar
    menuActual = "PRINCIPAL";
    inputBuffer = "";
    mostrarMenuPrincipal();
  } else if (key >= '0' && key <= '9') {
    if (inputBuffer.length() < 3) {
      inputBuffer += key;
      mostrarEliminarNumero();
    }
  }
}

void registrarVenta(String producto, int valor) {
  if (numVentas < 100) {
    ventas[numVentas].producto = producto;
    ventas[numVentas].valor = valor;
    ventas[numVentas].timestamp = obtenerTimestamp();
    numVentas++;
    Serial.println("Venta " + String(numVentas) + " registrada: " + producto + " - $" + String(valor));
  }
}

void eliminarVenta(int indice) {
  String productoEliminado = ventas[indice].producto;
  for (int i = indice; i < numVentas - 1; i++) {
    ventas[i] = ventas[i + 1];
  }
  numVentas--;
  Serial.println("Venta eliminada: " + productoEliminado);
}

String obtenerTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return "N/A";
  }
  char buffer[30];
  strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", &timeinfo);
  return String(buffer);
}

String obtenerFecha() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return "0000-00-00";
  }
  char buffer[15];
  strftime(buffer, sizeof(buffer), "%Y-%m-%d", &timeinfo);
  return String(buffer);
}

String generarReporteJSON() {
  DynamicJsonDocument doc(8192);
  
  doc["fecha"] = obtenerFecha();
  doc["total_ventas"] = numVentas;
  
  int totalDia = 0;
  JsonArray ventasArray = doc.createNestedArray("ventas");
  
  for (int i = 0; i < numVentas; i++) {
    JsonObject venta = ventasArray.createNestedObject();
    venta["numero"] = i + 1;
    venta["producto"] = ventas[i].producto;
    venta["valor"] = ventas[i].valor;
    venta["timestamp"] = ventas[i].timestamp;
    totalDia += ventas[i].valor;
  }
  
  doc["total_dia"] = totalDia;
  
  String output;
  serializeJson(doc, output);
  return output;
}

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
  display.println("Reporte del dia");
  display.println("enviado con exito!");
  display.println();
  display.println("Disponible en:");
  display.print("http://");
  display.println(WiFi.localIP());
  display.println("/reporte");
  display.display();
  
  Serial.println("=== REPORTE LISTO ===");
  Serial.println("URL: http://" + WiFi.localIP().toString() + "/reporte");
  Serial.println(generarReporteJSON());
  
  delay(4000);
  mostrarMenuPrincipal();
}

// ==================== FUNCIONES DE VISUALIZACIÓN ====================

void mostrarMenuPrincipal() {
  display.clearDisplay();
  display.setTextSize(1);
  
  // Título centrado
  display.setCursor(12, 2);
  display.println("MENU PRINCIPAL");
  
  // Línea separadora
  display.drawLine(0, 12, 128, 12, SH110X_WHITE);
  
  // Opciones
  display.setCursor(5, 20);
  display.println("A: Registrar venta");
  
  display.setCursor(5, 32);
  display.println("B: Eliminar venta");
  
  display.setCursor(5, 44);
  display.println("C: Enviar reporte");
  
  // Contador de ventas
  display.drawLine(0, 54, 128, 54, SH110X_WHITE);
  display.setCursor(5, 57);
  display.print("Ventas hoy: ");
  display.println(numVentas);
  
  display.display();
}

void mostrarRegistroProducto() {
  display.clearDisplay();
  display.setTextSize(1);
  
  // Título
  display.setCursor(5, 2);
  display.println("REGISTRAR VENTA");
  display.drawLine(0, 12, 128, 12, SH110X_WHITE);
  
  // Instrucción
  display.setCursor(5, 18);
  display.println("Codigo producto:");
  
  // Input grande
  display.setTextSize(2);
  display.setCursor(20, 35);
  display.println(inputBuffer);
  display.print("_");
  
  // Ayuda
  display.setTextSize(1);
  display.setCursor(5, 55);
  display.println("#=OK *=Borrar D=Salir");
  
  display.display();
}

void mostrarRegistroValor() {
  display.clearDisplay();
  display.setTextSize(1);
  
  // Título
  display.setCursor(5, 2);
  display.println("REGISTRAR VENTA");
  display.drawLine(0, 12, 128, 12, SH110X_WHITE);
  
  // Mostrar producto
  display.setCursor(5, 18);
  display.print("Producto: ");
  display.println(productoTemp);
  
  // Instrucción
  display.setCursor(5, 30);
  display.println("Valor vendido:");
  
  // Input grande
  display.setTextSize(1);
  display.setCursor(10, 42);
  display.print("$ ");
  display.setTextSize(2);
  display.print(inputBuffer);
  display.print("_");
  
  // Ayuda
  display.setTextSize(1);
  display.setCursor(5, 55);
  display.println("#=OK *=Borrar D=Salir");
  
  display.display();
}

void mostrarEliminarScroll() {
  display.clearDisplay();
  display.setTextSize(1);
  
  // Título
  display.setCursor(10, 2);
  display.println("ELIMINAR VENTA");
  display.drawLine(0, 12, 128, 12, SH110X_WHITE);
  
  // Subtítulo
  display.setCursor(5, 18);
  display.println("Ventas del dia:");
  
  // Mostrar venta actual
  display.setCursor(5, 30);
  display.setTextSize(1);
  display.print(ventaScrollPos + 1);
  display.print(". ");
  display.print(ventas[ventaScrollPos].producto);
  display.print(": $");
  display.println(ventas[ventaScrollPos].valor);
  
  // Instrucciones
  display.setCursor(5, 44);
  display.println("Presione 0 para");
  display.setCursor(5, 52);
  display.println("elegir venta");
  
  // Navegación
  display.drawLine(0, 54, 128, 54, SH110X_WHITE);
  display.setCursor(2, 57);
  display.print("*=Ant #=Sig ");
  display.print(ventaScrollPos + 1);
  display.print("/");
  display.print(numVentas);
  
  display.display();
}

void mostrarEliminarNumero() {
  display.clearDisplay();
  display.setTextSize(1);
  
  // Título
  display.setCursor(10, 2);
  display.println("ELIMINAR VENTA");
  display.drawLine(0, 12, 128, 12, SH110X_WHITE);
  
  // Instrucción
  display.setCursor(5, 22);
  display.println("Numero de venta");
  display.setCursor(5, 32);
  display.println("a eliminar:");
  
  // Input grande
  display.setTextSize(2);
  display.setCursor(50, 42);
  display.print(inputBuffer);
  display.print("_");
  
  // Ayuda
  display.setTextSize(1);
  display.setCursor(5, 55);
  display.println("#=OK *=Borrar D=Salir");
  
  display.display();
}

void mostrarMensajeVentaRegistrada() {
  display.clearDisplay();
  display.setTextSize(1);
  
  display.setCursor(15, 15);
  display.println("VENTA NUMERO");
  
  display.setTextSize(3);
  display.setCursor(50, 30);
  display.println(numVentas);
  
  display.setTextSize(1);
  display.setCursor(10, 52);
  display.println("Registrada con");
  display.setCursor(35, 60);
  display.println("exito!");
  
  display.display();
}

void mostrarMensajeTemporal(const char* mensaje) {
  display.clearDisplay();
  display.setTextSize(1);
  
  // Centrar mensaje
  int y = 25;
  String msg = String(mensaje);
  int start = 0;
  int newlinePos = msg.indexOf('\n');
  
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