from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import io
import json
import os
import base64
from pathlib import Path
import tempfile
import shutil

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для работы с разных устройств

# Глобальные переменные для хранения состояния
pdf_documents = {}  # {session_id: fitz.Document}
pdf_data = {}  # {session_id: {deletion_areas, color_changes, etc.}}
upload_dir = Path(tempfile.gettempdir()) / "pdf_editor_uploads"
upload_dir.mkdir(exist_ok=True)


def apply_changes_to_image(img, page_num, session_id, zoom=1.0):
    """Применение изменений к изображению"""
    from PIL import ImageDraw
    
    if session_id not in pdf_data:
        return img
    
    data = pdf_data[session_id]
    deletion_areas = data.get('deletion_areas', [])
    color_changes = data.get('color_changes', [])
    color_replacements = data.get('color_replacements', [])
    inserted_content = data.get('inserted_content', [])
    
    img_copy = img.copy()
    draw = ImageDraw.Draw(img_copy)
    
    # Применение удалений
    if page_num < len(deletion_areas):
        for area in deletion_areas[page_num]:
            x1, y1, x2, y2 = area
            x1_scaled = int(x1 * zoom)
            y1_scaled = int(y1 * zoom)
            x2_scaled = int(x2 * zoom)
            y2_scaled = int(y2 * zoom)
            
            x1_scaled = max(0, min(x1_scaled, img.width))
            y1_scaled = max(0, min(y1_scaled, img.height))
            x2_scaled = max(0, min(x2_scaled, img.width))
            y2_scaled = max(0, min(y2_scaled, img.height))
            
            if x1_scaled < x2_scaled and y1_scaled < y2_scaled:
                draw.rectangle([x1_scaled, y1_scaled, x2_scaled, y2_scaled], 
                             fill=(255, 255, 255), outline=None)
    
    # Применение замены цвета в областях
    if page_num < len(color_changes):
        for change in color_changes[page_num]:
            area, orig_color, new_color = change
            x1, y1, x2, y2 = area
            x1_scaled = int(x1 * zoom)
            y1_scaled = int(y1 * zoom)
            x2_scaled = int(x2 * zoom)
            y2_scaled = int(y2 * zoom)
            
            x1_scaled = max(0, min(x1_scaled, img.width))
            y1_scaled = max(0, min(y1_scaled, img.height))
            x2_scaled = max(0, min(x2_scaled, img.width))
            y2_scaled = max(0, min(y2_scaled, img.height))
            
            if x1_scaled < x2_scaled and y1_scaled < y2_scaled:
                if new_color and new_color.startswith('#'):
                    try:
                        r = int(new_color[1:3], 16)
                        g = int(new_color[3:5], 16)
                        b = int(new_color[5:7], 16)
                        draw.rectangle([x1_scaled, y1_scaled, x2_scaled, y2_scaled], 
                                     fill=(r, g, b), outline=None)
                    except (ValueError, IndexError):
                        pass
    
    # Применение замены цвета на всей странице
    if page_num < len(color_replacements) and color_replacements[page_num]:
        pixels = img_copy.load()
        width, height = img_copy.size
        
        for replacement in color_replacements[page_num]:
            old_color_hex = replacement['old_color']
            new_color_hex = replacement['new_color']
            tolerance = replacement.get('tolerance', 30)
            
            try:
                old_r = int(old_color_hex[1:3], 16)
                old_g = int(old_color_hex[3:5], 16)
                old_b = int(old_color_hex[5:7], 16)
                
                new_r = int(new_color_hex[1:3], 16)
                new_g = int(new_color_hex[3:5], 16)
                new_b = int(new_color_hex[5:7], 16)
            except (ValueError, IndexError):
                continue
            
            for y in range(height):
                for x in range(width):
                    r, g, b = pixels[x, y]
                    color_distance = ((r - old_r)**2 + (g - old_g)**2 + (b - old_b)**2)**0.5
                    if color_distance <= tolerance:
                        pixels[x, y] = (new_r, new_g, new_b)
    
    # Применение вставленного контента
    for content in inserted_content:
        if content['page'] == page_num:
            x = int(content['x'] * zoom)
            y = int(content['y'] * zoom)
            
            if content['type'] == 'text':
                try:
                    text = content['data']['text']
                    font_size = content['data']['font_size']
                    color_hex = content['data']['color']
                    
                    r = int(color_hex[1:3], 16)
                    g = int(color_hex[3:5], 16)
                    b = int(color_hex[5:7], 16)
                    
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        try:
                            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                        except:
                            font = ImageFont.load_default()
                    
                    draw.text((x, y), text, fill=(r, g, b), font=font)
                except Exception:
                    pass
            
            elif content['type'] == 'image':
                try:
                    img_path = content['data']['path']
                    if Path(img_path).exists():
                        insert_img = Image.open(img_path)
                        
                        width = content['data']['width']
                        height = content['data']['height']
                        if width > 0 or height > 0:
                            if width > 0 and height > 0:
                                insert_img = insert_img.resize((width, height), Image.Resampling.LANCZOS)
                            elif width > 0:
                                ratio = width / insert_img.width
                                insert_img = insert_img.resize((width, int(insert_img.height * ratio)), Image.Resampling.LANCZOS)
                            elif height > 0:
                                ratio = height / insert_img.height
                                insert_img = insert_img.resize((int(insert_img.width * ratio), height), Image.Resampling.LANCZOS)
                        
                        img_copy.paste(insert_img, (x, y), insert_img if insert_img.mode == 'RGBA' else None)
                except Exception:
                    pass
    
    return img_copy


@app.route('/')
def index():
    """Главная страница"""
    try:
        return render_template('index.html')
    except Exception as e:
        return f"Ошибка загрузки шаблона: {str(e)}", 500


@app.route('/health')
def health():
    """Проверка работоспособности сервера"""
    return jsonify({'status': 'ok', 'message': 'Server is running'})


@app.route('/test')
def test():
    """Простая тестовая страница для проверки работы"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Тест подключения</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                padding: 20px;
                text-align: center;
            }
            .success { color: green; }
            .error { color: red; }
        </style>
    </head>
    <body>
        <h1>PDF Editor - Тест подключения</h1>
        <p class="success">✅ Сервер работает!</p>
        <p><a href="/">Вернуться к редактору</a></p>
        <script>
            fetch('/health')
                .then(r => r.json())
                .then(d => {
                    document.body.innerHTML += '<p class="success">✅ API доступен: ' + d.message + '</p>';
                })
                .catch(e => {
                    document.body.innerHTML += '<p class="error">❌ Ошибка API: ' + e + '</p>';
                });
        </script>
    </body>
    </html>
    """


@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    """Загрузка PDF файла"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Сохраняем файл временно
        session_id = request.form.get('session_id', 'default')
        file_path = upload_dir / f"{session_id}_{file.filename}"
        file.save(str(file_path))
        
        # Открываем PDF
        pdf_doc = fitz.open(str(file_path))
        total_pages = len(pdf_doc)
        
        if total_pages == 0:
            return jsonify({'error': 'PDF file is empty'}), 400
        
        # Сохраняем документ
        pdf_documents[session_id] = pdf_doc
        
        # Инициализируем данные
        pdf_data[session_id] = {
            'deletion_areas': [[] for _ in range(total_pages)],
            'color_changes': [[] for _ in range(total_pages)],
            'color_replacements': [[] for _ in range(total_pages)],
            'inserted_content': [],
            'file_path': str(file_path)
        }
        
        return jsonify({
            'success': True,
            'total_pages': total_pages,
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/page/<int:page_num>')
def get_page(page_num):
    """Получение изображения страницы"""
    session_id = request.args.get('session_id', 'default')
    zoom = float(request.args.get('zoom', 1.0))
    apply_changes = request.args.get('apply_changes', 'true').lower() == 'true'
    
    if session_id not in pdf_documents:
        return jsonify({'error': 'PDF not loaded'}), 400
    
    try:
        pdf_doc = pdf_documents[session_id]
        if page_num < 0 or page_num >= len(pdf_doc):
            return jsonify({'error': 'Invalid page number'}), 400
        
        page = pdf_doc[page_num]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Применяем изменения, если нужно
        if apply_changes and session_id in pdf_data:
            img = apply_changes_to_image(img, page_num, session_id, zoom)
        
        # Конвертируем в base64
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        img_base64 = base64.b64encode(img_bytes.read()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': f'data:image/png;base64,{img_base64}',
            'width': img.width,
            'height': img.height,
            'page_width': page.rect.width,
            'page_height': page.rect.height
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/add_deletion', methods=['POST'])
def add_deletion():
    """Добавление области для удаления"""
    data = request.json
    session_id = data.get('session_id', 'default')
    page_num = data.get('page_num', 0)
    area = data.get('area')  # [x1, y1, x2, y2]
    
    if session_id not in pdf_data:
        return jsonify({'error': 'PDF not loaded'}), 400
    
    if page_num < len(pdf_data[session_id]['deletion_areas']):
        pdf_data[session_id]['deletion_areas'][page_num].append(area)
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid page number'}), 400


@app.route('/api/add_color_change', methods=['POST'])
def add_color_change():
    """Добавление замены цвета"""
    data = request.json
    session_id = data.get('session_id', 'default')
    page_num = data.get('page_num', 0)
    area = data.get('area')
    orig_color = data.get('orig_color')
    new_color = data.get('new_color')
    
    if session_id not in pdf_data:
        return jsonify({'error': 'PDF not loaded'}), 400
    
    if page_num < len(pdf_data[session_id]['color_changes']):
        pdf_data[session_id]['color_changes'][page_num].append([area, orig_color, new_color])
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid page number'}), 400


@app.route('/api/add_color_replacement', methods=['POST'])
def add_color_replacement():
    """Добавление замены цвета на всю страницу"""
    data = request.json
    session_id = data.get('session_id', 'default')
    page_num = data.get('page_num', 0)
    old_color = data.get('old_color')
    new_color = data.get('new_color')
    tolerance = data.get('tolerance', 30)
    
    if session_id not in pdf_data:
        return jsonify({'error': 'PDF not loaded'}), 400
    
    if page_num < len(pdf_data[session_id]['color_replacements']):
        pdf_data[session_id]['color_replacements'][page_num].append({
            'old_color': old_color,
            'new_color': new_color,
            'tolerance': tolerance
        })
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid page number'}), 400


@app.route('/api/add_content', methods=['POST'])
def add_content():
    """Добавление вставленного контента"""
    data = request.json
    session_id = data.get('session_id', 'default')
    
    if session_id not in pdf_data:
        return jsonify({'error': 'PDF not loaded'}), 400
    
    # Обработка загрузки изображения, если есть
    if 'image' in request.files:
        file = request.files['image']
        if file.filename:
            file_path = upload_dir / f"{session_id}_img_{file.filename}"
            file.save(str(file_path))
            data['data']['path'] = str(file_path)
    
    pdf_data[session_id]['inserted_content'].append({
        'page': data.get('page_num', 0),
        'type': data.get('type'),
        'x': data.get('x'),
        'y': data.get('y'),
        'data': data.get('data')
    })
    
    return jsonify({'success': True})


@app.route('/api/delete_item', methods=['POST'])
def delete_item():
    """Удаление элемента"""
    data = request.json
    session_id = data.get('session_id', 'default')
    item_type = data.get('type')  # 'deletion', 'color', 'content'
    page_num = data.get('page_num', 0)
    index = data.get('index', -1)
    
    if session_id not in pdf_data:
        return jsonify({'error': 'PDF not loaded'}), 400
    
    try:
        if item_type == 'deletion' and page_num < len(pdf_data[session_id]['deletion_areas']):
            if 0 <= index < len(pdf_data[session_id]['deletion_areas'][page_num]):
                del pdf_data[session_id]['deletion_areas'][page_num][index]
        elif item_type == 'color' and page_num < len(pdf_data[session_id]['color_changes']):
            if 0 <= index < len(pdf_data[session_id]['color_changes'][page_num]):
                del pdf_data[session_id]['color_changes'][page_num][index]
        elif item_type == 'content':
            content_list = pdf_data[session_id]['inserted_content']
            if 0 <= index < len(content_list) and content_list[index]['page'] == page_num:
                del content_list[index]
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/save', methods=['POST'])
def save_pdf():
    """Сохранение PDF"""
    data = request.json
    session_id = data.get('session_id', 'default')
    
    if session_id not in pdf_documents:
        return jsonify({'error': 'PDF not loaded'}), 400
    
    try:
        pdf_doc = pdf_documents[session_id]
        pdf_info = pdf_data[session_id]
        
        # Создаем новый документ
        new_doc = fitz.open()
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            page_rect = page.rect
            
            # Проверяем, нужны ли изменения через изображение
            has_full_page_color_replacements = (
                page_num < len(pdf_info['color_replacements']) and 
                pdf_info['color_replacements'][page_num]
            )
            has_inserted_content = any(
                c['page'] == page_num for c in pdf_info['inserted_content']
            )
            
            new_page = new_doc.new_page(width=page_rect.width, height=page_rect.height)
            
            if has_full_page_color_replacements or has_inserted_content:
                # Используем изображение
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img = apply_changes_to_image(img, page_num, session_id, 1.0)
                
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                
                img_rect = fitz.Rect(0, 0, page_rect.width, page_rect.height)
                new_page.insert_image(img_rect, stream=img_bytes.getvalue())
            else:
                # Используем векторную графику
                new_page.show_pdf_page(new_page.rect, pdf_doc, page_num)
                
                # Применяем удаления
                if page_num < len(pdf_info['deletion_areas']):
                    for area in pdf_info['deletion_areas'][page_num]:
                        x1, y1, x2, y2 = area
                        x1 = max(0, min(x1, page_rect.width))
                        y1 = max(0, min(y1, page_rect.height))
                        x2 = max(0, min(x2, page_rect.width))
                        y2 = max(0, min(y2, page_rect.height))
                        
                        if x1 < x2 and y1 < y2:
                            rect = fitz.Rect(x1, y1, x2, y2)
                            new_page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                
                # Применяем замены цвета
                if page_num < len(pdf_info['color_changes']):
                    for change in pdf_info['color_changes'][page_num]:
                        area, orig_color, new_color = change
                        x1, y1, x2, y2 = area
                        x1 = max(0, min(x1, page_rect.width))
                        y1 = max(0, min(y1, page_rect.height))
                        x2 = max(0, min(x2, page_rect.width))
                        y2 = max(0, min(y2, page_rect.height))
                        
                        if x1 < x2 and y1 < y2:
                            rect = fitz.Rect(x1, y1, x2, y2)
                            if new_color and new_color.startswith('#'):
                                try:
                                    r = int(new_color[1:3], 16) / 255.0
                                    g = int(new_color[3:5], 16) / 255.0
                                    b = int(new_color[5:7], 16) / 255.0
                                    new_page.draw_rect(rect, color=(r, g, b), fill=(r, g, b))
                                except (ValueError, IndexError):
                                    pass
                
                # Применяем вставленный контент
                for content in pdf_info['inserted_content']:
                    if content['page'] == page_num:
                        try:
                            if content['type'] == 'text':
                                text = content['data']['text']
                                font_size = content['data']['font_size']
                                color_hex = content['data']['color']
                                
                                r = int(color_hex[1:3], 16) / 255.0
                                g = int(color_hex[3:5], 16) / 255.0
                                b = int(color_hex[5:7], 16) / 255.0
                                
                                point = fitz.Point(content['x'], content['y'])
                                new_page.insert_text(point, text, fontsize=font_size, color=(r, g, b))
                            
                            elif content['type'] == 'image':
                                img_path = content['data']['path']
                                if Path(img_path).exists():
                                    img = Image.open(img_path)
                                    width = content['data']['width']
                                    height = content['data']['height']
                                    
                                    if width > 0 or height > 0:
                                        if width > 0 and height > 0:
                                            img = img.resize((width, height), Image.Resampling.LANCZOS)
                                        elif width > 0:
                                            ratio = width / img.width
                                            img = img.resize((width, int(img.height * ratio)), Image.Resampling.LANCZOS)
                                        elif height > 0:
                                            ratio = height / img.height
                                            img = img.resize((int(img.width * ratio), height), Image.Resampling.LANCZOS)
                                    
                                    img_bytes = io.BytesIO()
                                    img.save(img_bytes, format='PNG')
                                    img_bytes.seek(0)
                                    
                                    rect = fitz.Rect(
                                        content['x'],
                                        content['y'],
                                        content['x'] + img.width,
                                        content['y'] + img.height
                                    )
                                    new_page.insert_image(rect, stream=img_bytes.getvalue())
                        except Exception:
                            pass
        
        # Сохраняем во временный файл
        output_path = upload_dir / f"{session_id}_output.pdf"
        new_doc.save(str(output_path))
        new_doc.close()
        
        return send_file(str(output_path), as_attachment=True, download_name='edited.pdf')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear', methods=['POST'])
def clear_page():
    """Очистка всех изменений на странице"""
    data = request.json
    session_id = data.get('session_id', 'default')
    page_num = data.get('page_num', 0)
    
    if session_id not in pdf_data:
        return jsonify({'error': 'PDF not loaded'}), 400
    
    if page_num < len(pdf_data[session_id]['deletion_areas']):
        pdf_data[session_id]['deletion_areas'][page_num] = []
    if page_num < len(pdf_data[session_id]['color_changes']):
        pdf_data[session_id]['color_changes'][page_num] = []
    if page_num < len(pdf_data[session_id]['color_replacements']):
        pdf_data[session_id]['color_replacements'][page_num] = []
    
    # Удаляем вставленный контент на этой странице
    pdf_data[session_id]['inserted_content'] = [
        c for c in pdf_data[session_id]['inserted_content'] if c['page'] != page_num
    ]
    
    return jsonify({'success': True})


@app.route('/api/get_page_data')
def get_page_data():
    """Получение данных изменений для страницы"""
    session_id = request.args.get('session_id', 'default')
    page_num = int(request.args.get('page_num', 0))
    
    if session_id not in pdf_data:
        return jsonify({'error': 'PDF not loaded'}), 400
    
    data = pdf_data[session_id]
    
    return jsonify({
        'success': True,
        'deletion_areas': data['deletion_areas'][page_num] if page_num < len(data['deletion_areas']) else [],
        'color_changes': data['color_changes'][page_num] if page_num < len(data['color_changes']) else [],
        'color_replacements': data['color_replacements'][page_num] if page_num < len(data['color_replacements']) else [],
        'inserted_content': [c for c in data['inserted_content'] if c['page'] == page_num]
    })


@app.route('/api/apply_to_page', methods=['POST'])
def apply_to_page():
    """Применение изменений с одной страницы на другую"""
    data = request.json
    session_id = data.get('session_id', 'default')
    source_page = data.get('source_page', 0)
    target_page = data.get('target_page', 0)
    source_data = data.get('data', {})
    
    if session_id not in pdf_data:
        return jsonify({'error': 'PDF not loaded'}), 400
    
    pdf_info = pdf_data[session_id]
    
    try:
        # Копируем области удаления
        if source_page < len(pdf_info['deletion_areas']):
            deletion_areas = pdf_info['deletion_areas'][source_page].copy()
            if target_page < len(pdf_info['deletion_areas']):
                pdf_info['deletion_areas'][target_page].extend(deletion_areas)
            else:
                while len(pdf_info['deletion_areas']) <= target_page:
                    pdf_info['deletion_areas'].append([])
                pdf_info['deletion_areas'][target_page] = deletion_areas
        
        # Копируем замены цвета (области)
        if source_page < len(pdf_info['color_changes']):
            color_changes = pdf_info['color_changes'][source_page].copy()
            if target_page < len(pdf_info['color_changes']):
                pdf_info['color_changes'][target_page].extend(color_changes)
            else:
                while len(pdf_info['color_changes']) <= target_page:
                    pdf_info['color_changes'].append([])
                pdf_info['color_changes'][target_page] = color_changes
        
        # Копируем замены цвета (вся страница)
        if source_page < len(pdf_info['color_replacements']):
            color_replacements = pdf_info['color_replacements'][source_page].copy()
            if target_page < len(pdf_info['color_replacements']):
                pdf_info['color_replacements'][target_page].extend(color_replacements)
            else:
                while len(pdf_info['color_replacements']) <= target_page:
                    pdf_info['color_replacements'].append([])
                pdf_info['color_replacements'][target_page] = color_replacements
        
        # Копируем вставленный контент
        source_content = [c.copy() for c in pdf_info['inserted_content'] if c['page'] == source_page]
        for content in source_content:
            content['page'] = target_page
            pdf_info['inserted_content'].append(content)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Запуск на всех интерфейсах для доступа с iPad
    # Используем порт 5001, так как 5000 часто занят AirPlay на macOS
    app.run(host='0.0.0.0', port=5001, debug=True)

