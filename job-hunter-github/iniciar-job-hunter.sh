#!/usr/bin/env bash
# 🦅 Job Hunter - iniciar en Mac/Linux
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  🦅 Job Hunter - iniciando..."
echo "============================================"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] No se encontró Python 3. Instalalo desde https://www.python.org/downloads/"
  exit 1
fi
echo "[OK] Python encontrado"

if [ ! -f ".deps_instalado" ]; then
  echo "Instalando dependencias (solo la primera vez)..."
  python3 -m pip install -q --upgrade pip
  python3 -m pip install -q -r requirements.txt
  touch .deps_instalado
  echo "[OK] Dependencias instaladas"
fi

echo "[OK] Arrancando... tu app quedará en http://localhost:8000"
echo "     Dejá esta ventana abierta mientras la uses (Ctrl+C para cerrar)."
echo
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
