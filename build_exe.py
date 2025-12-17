#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для сборки exe файла из main.py (десктопное приложение)
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
    
    # Используем ASCII-совместимые сообщения для совместимости
    print("Starting EXE build...")
    print(f"Parameters: {' '.join(args)}")
    
    try:
        PyInstaller.__main__.run(args)
        print("\n[SUCCESS] Build completed successfully!")
        if sys.platform == 'darwin':  # macOS
            print("[INFO] Application is in: dist/PDFEditor.app")
        elif sys.platform == 'win32':  # Windows
            print("[INFO] EXE file is in: dist/PDFEditor.exe")
        else:  # Linux
            print("[INFO] Executable is in: dist/PDFEditor")
    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    build_exe()

