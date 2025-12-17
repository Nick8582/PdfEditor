#!/usr/bin/env python3
"""
Скрипт для сборки exe файла из app.py (веб-приложение Flask)
"""
import PyInstaller.__main__
import sys
import os

def build_web_exe():
    """Собирает exe файл из app.py для веб-сервера"""
    
    # Определяем правильный разделитель для текущей платформы
    # Windows использует ';', Unix использует ':'
    path_sep = ';' if sys.platform == 'win32' else ':'
    
    # Параметры для PyInstaller
    args = [
        'app.py',
        '--name=PDFEditorWeb',
        '--onefile',  # Один exe файл
        '--console',  # С консолью (для веб-сервера нужна консоль)
        f'--add-data=templates{path_sep}templates',  # Включаем папку templates
        '--hidden-import=flask',
        '--hidden-import=flask_cors',
        '--hidden-import=PIL._tkinter_finder',
        '--collect-all=PIL',
        '--collect-all=fitz',
        '--collect-all=flask',
        '--clean',
    ]
    
    print("Начинаем сборку exe файла для веб-приложения...")
    print(f"Параметры: {' '.join(args)}")
    
    try:
        PyInstaller.__main__.run(args)
        print("\n✅ Сборка завершена успешно!")
        print("📁 exe файл находится в папке: dist/PDFEditorWeb.exe")
        print("\n💡 Для запуска веб-сервера запустите: dist/PDFEditorWeb.exe")
    except Exception as e:
        print(f"\n❌ Ошибка при сборке: {e}")
        sys.exit(1)

if __name__ == '__main__':
    build_web_exe()

