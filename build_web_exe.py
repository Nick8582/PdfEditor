#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для сборки exe файла из app.py (веб-приложение Flask)
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
    
    # Используем ASCII-совместимые сообщения для совместимости
    print("Starting web EXE build...")
    print(f"Parameters: {' '.join(args)}")
    
    try:
        PyInstaller.__main__.run(args)
        print("\n[SUCCESS] Build completed successfully!")
        print("[INFO] EXE file is in: dist/PDFEditorWeb.exe")
        print("\n[INFO] To start web server, run: dist/PDFEditorWeb.exe")
    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    build_web_exe()

