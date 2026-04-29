#!/bin/bash
# ================================================
#  Lanzador del Sistema de Ventas
#  Coloca este archivo en la misma carpeta que app.py
# ================================================

VENV="$HOME/venv-ventas"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. Crear entorno virtual si no existe
if [ ! -d "$VENV" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv "$VENV"
fi

# 2. Activar entorno
source "$VENV/bin/activate"

# 3. Instalar dependencias si faltan
echo "Verificando dependencias..."
pip install customtkinter mysql-connector-python requests -q

# 4. Verificar tkinter
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Instalando tkinter..."
    sudo apt install python3-tk -y
fi

# 5. Correr la app
echo "Iniciando Sistema de Ventas..."
cd "$APP_DIR"
python app.py
