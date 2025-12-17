#!/usr/bin/env python3
"""
Скрипт для сборки exe файла из main.py (десктопное приложение)
"""
import PyInstaller.__main__
import sys
import os

def build_exe():
    """Собирает exe файл из main.py"""
    
    # Параметры для PyInstaller
    args = [
        'main.py',
        '--name=PDFEditor',
        '--onefile',  # Один exe файл
        '--windowed',  # Без консоли (для GUI приложения)
        # Иконку можно добавить позже: '--icon=icon.ico'
        '--hidden-import=PIL._tkinter_finder',  # Для работы с PIL
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=tkinter.filedialog',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=tkinter.colorchooser',
        '--collect-all=PIL',  # Собираем все модули PIL
        '--collect-all=fitz',  # Собираем все модули PyMuPDF
        '--clean',  # Очистить кэш перед сборкой
    ]
    
    # Если на Windows, добавляем специфичные параметры
    if sys.platform == 'win32':
        args.append('--noconsole')
    
    print("Начинаем сборку exe файла...")
    print(f"Параметры: {' '.join(args)}")
    
    try:
        PyInstaller.__main__.run(args)
        print("\n✅ Сборка завершена успешно!")
        if sys.platform == 'darwin':  # macOS
            print("📁 Приложение находится в папке: dist/PDFEditor.app")
        elif sys.platform == 'win32':  # Windows
            print("📁 exe файл находится в папке: dist/PDFEditor.exe")
        else:  # Linux
            print("📁 Исполняемый файл находится в папке: dist/PDFEditor")
    except Exception as e:
        print(f"\n❌ Ошибка при сборке: {e}")
        sys.exit(1)

if __name__ == '__main__':
    build_exe()

