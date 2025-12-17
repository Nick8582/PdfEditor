#!/bin/bash
# Скрипт для запуска сборки Windows exe через GitHub Actions

echo "========================================"
echo "Сборка Windows EXE через GitHub Actions"
echo "========================================"
echo ""

# Проверка наличия git
if ! command -v git &> /dev/null; then
    echo "❌ Git не найден! Установите Git с git-scm.com"
    exit 1
fi

# Проверка наличия gh (GitHub CLI)
if ! command -v gh &> /dev/null; then
    echo "⚠️  GitHub CLI (gh) не найден."
    echo ""
    echo "Установите GitHub CLI:"
    echo "  macOS: brew install gh"
    echo "  Или скачайте с: https://cli.github.com/"
    echo ""
    echo "После установки выполните: gh auth login"
    echo ""
    read -p "Продолжить без GitHub CLI? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    USE_GH=false
else
    USE_GH=true
fi

# Проверка, что мы в git репозитории
if [ ! -d .git ]; then
    echo "⚠️  Текущая папка не является git репозиторием."
    echo ""
    read -p "Инициализировать git репозиторий? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git init
        git add .
        git commit -m "Initial commit"
        echo "✅ Git репозиторий инициализирован"
    else
        echo "❌ Нужен git репозиторий для работы с GitHub Actions"
        exit 1
    fi
fi

# Проверка наличия .github/workflows
if [ ! -d .github/workflows ]; then
    mkdir -p .github/workflows
    echo "✅ Создана папка .github/workflows"
fi

# Проверка наличия workflow файла
if [ ! -f .github/workflows/build-windows.yml ]; then
    echo "⚠️  Файл .github/workflows/build-windows.yml не найден!"
    echo "Создайте его вручную или используйте готовый из проекта."
    exit 1
fi

echo "📤 Отправка кода на GitHub..."
echo ""

# Проверка наличия remote
if ! git remote | grep -q origin; then
    echo "⚠️  Remote 'origin' не настроен."
    echo ""
    read -p "Введите URL вашего GitHub репозитория (или нажмите Enter для пропуска): " REPO_URL
    if [ ! -z "$REPO_URL" ]; then
        git remote add origin "$REPO_URL"
        echo "✅ Remote добавлен"
    else
        echo "❌ Нужен настроенный GitHub репозиторий"
        exit 1
    fi
fi

# Коммит изменений (если есть)
if ! git diff-index --quiet HEAD --; then
    echo "📝 Обнаружены несохраненные изменения"
    git add .
    git commit -m "Update project files"
fi

# Отправка на GitHub
echo "📤 Отправка на GitHub..."
git push origin HEAD

if [ "$USE_GH" = true ]; then
    echo ""
    echo "🚀 Запуск GitHub Actions workflow..."
    gh workflow run build-windows.yml
    
    echo ""
    echo "✅ Workflow запущен!"
    echo ""
    echo "📊 Отслеживать прогресс можно здесь:"
    echo "   https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
    echo ""
    echo "💡 После завершения сборки скачайте exe файлы из раздела 'Artifacts'"
else
    echo ""
    echo "📊 Откройте GitHub репозиторий и перейдите в раздел 'Actions'"
    echo "   Запустите workflow 'Build Windows EXE' вручную"
    echo ""
    echo "💡 После завершения сборки скачайте exe файлы из раздела 'Artifacts'"
fi

echo ""
echo "========================================"

