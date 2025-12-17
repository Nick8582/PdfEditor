#!/bin/bash

# Скрипт для запуска веб-версии PDF Editor

echo "🚀 Запуск веб-версии PDF Editor..."
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.7 или выше."
    exit 1
fi

# Проверка зависимостей
echo "📦 Проверка зависимостей..."
python3 -c "import flask" 2>/dev/null || {
    echo "⚠️  Flask не установлен. Устанавливаю..."
    pip3 install Flask flask-cors
}

# Получение IP адреса
echo ""
echo "📡 IP адреса для доступа с iPad:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print "   http://" $2 ":5001"}'
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127.0.0.1 | awk '{print "   http://" $1 ":5000"}'
else
    echo "   Проверьте IP адрес вручную и используйте: http://[IP]:5000"
fi

echo ""
echo "🌐 Откройте браузер и перейдите на http://localhost:5001"
echo "📱 На iPad откройте Safari и введите адрес выше"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo ""

# Запуск сервера
python3 app.py

