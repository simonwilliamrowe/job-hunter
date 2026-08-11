@echo off
chcp 65001 >nul
title Job Hunter
echo ============================================
echo   🦅 Job Hunter - iniciando...
echo ============================================
echo.

REM --- Paso 1: verificar Python ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se encontro Python.
    echo Bajalo de https://www.python.org/downloads/ y marcala la casilla
    echo "Add Python to PATH" al instalarlo. Despues volve a correr este archivo.
    pause
    exit /b 1
)
echo [OK] Python encontrado

REM --- Paso 2: instalar dependencias (solo la primera vez) ---
if not exist ".deps_instalado" (
    echo.
    echo Instalando dependencias (solo la primera vez)...
    python -m pip install -q --upgrade pip
    python -m pip install -q -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion. Revisa tu conexion a internet.
        pause
        exit /b 1
    )
    echo .deps_instalado > .deps_instalado
    echo [OK] Dependencias instaladas
)

REM --- Paso 3: arrancar el servidor ---
echo.
echo [OK] Arrancando... tu app quedara en http://localhost:8000
echo      Deja esta ventana abierta mientras la uses.
echo      Para cerrarla: tacha esta ventana o presiona Ctrl+C
echo.
python -m uvicorn app:app --host 0.0.0.0 --port 8000
pause
