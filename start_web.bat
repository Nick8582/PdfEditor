@echo off
REM Скрипт для запуска веб-версии PDF Editor на Windows

echo.
echo Запуск веб-версии PDF Editor...
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Ошибка: Python не найден. Установите Python 3.7 или выше.
    pause
    exit /b 1
)

REM Проверка зависимостей
echo Проверка зависимостей...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo Установка Flask...
    pip install Flask flask-cors
)

REM Получение IP адреса
echo.
echo IP адреса для доступа с iPad:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set ip=%%a
    set ip=!ip:~1!
    echo    http://!ip!:5001
)

echo.
echo Откройте браузер и перейдите на http://localhost:5001
echo На iPad откройте Safari и введите адрес выше
echo.
echo Для остановки нажмите Ctrl+C
echo.

REM Запуск сервера
python app.py

pause

