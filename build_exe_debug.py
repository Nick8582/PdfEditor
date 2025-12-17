#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для сборки exe файла с консолью для отладки (десктопное приложение)
"""
import PyInstaller.__main__
import sys
import os
import io

# Устанавливаем UTF-8 для вывода (для поддержки эмодзи и кириллицы)
if sys.platform == 'win32':
    # На Windows устанавливаем UTF-8 для stdout
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

def build_exe_debug():
    """Собирает exe файл из main.py с консолью для отладки"""
    
    # Параметры для PyInstaller
    args = [
        'main.py',
        '--name=PDFEditor_debug',
        '--onefile',  # Один exe файл
        '--console',  # С консолью для отладки
        # Иконку можно добавить позже: '--icon=icon.ico'
        
        # Tkinter импорты
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=tkinter.filedialog',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=tkinter.colorchooser',
        '--hidden-import=tkinter.font',
        
        # PIL/Pillow импорты
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=PIL.Image',
        '--hidden-import=PIL.ImageTk',
        '--hidden-import=PIL.ImageDraw',
        '--hidden-import=PIL.ImageFont',
        '--hidden-import=PIL._imagingtk',
        '--collect-all=PIL',  # Собираем все модули PIL
        
        # PyMuPDF импорты
        '--hidden-import=fitz',
        '--hidden-import=fitz.utils',
        '--collect-all=fitz',  # Собираем все модули PyMuPDF
        
        # Стандартные библиотеки
        '--hidden-import=json',
        '--hidden-import=io',
        '--hidden-import=pathlib',
        
        # Дополнительные настройки для стабильности
        '--noupx',  # Отключаем UPX для избежания проблем с антивирусами
        '--clean',  # Очистить кэш перед сборкой
    ]
    
    # Если на Windows, добавляем специфичные параметры
    if sys.platform == 'win32':
        # На Windows добавляем обработку путей
        args.append('--paths=.')
    
    # Используем ASCII-совместимые сообщения для совместимости
    print("Starting DEBUG EXE build (with console)...")
    print(f"Parameters: {' '.join(args)}")
    
    try:
        PyInstaller.__main__.run(args)
        print("\n[SUCCESS] Debug build completed successfully!")
        if sys.platform == 'darwin':  # macOS
            print("[INFO] Application is in: dist/PDFEditor_debug.app")
        elif sys.platform == 'win32':  # Windows
            print("[INFO] EXE file is in: dist/PDFEditor_debug.exe")
            print("[INFO] This version has console enabled for debugging")
        else:  # Linux
            print("[INFO] Executable is in: dist/PDFEditor_debug")
    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    build_exe_debug()

