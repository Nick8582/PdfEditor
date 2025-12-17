@echo off
chcp 65001 >nul
echo ========================================
echo Сборка exe файла для PDF Editor
echo ========================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python с python.org
    pause
    exit /b 1
)

REM Проверка наличия PyInstaller
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo 📦 Устанавливаем PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo ❌ Не удалось установить PyInstaller
        pause
        exit /b 1
    )
)

echo 🔨 Начинаем сборку...
echo.

REM Запуск скрипта сборки
python build_exe.py

if errorlevel 1 (
    echo.
    echo ❌ Ошибка при сборке!
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ Готово! exe файл находится в папке dist/
echo ========================================
pause

