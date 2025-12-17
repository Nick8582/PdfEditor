import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk
import fitz  # PyMuPDF
import io
import json
from pathlib import Path


class PDFEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Editor - Редактор PDF")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # Настройка стиля
        style = ttk.Style()
        style.theme_use('clam')  # Более современная тема
        
        self.pdf_document = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom = 1.0
        self.deletion_areas = []  # Список областей для удаления
        self.color_changes = []   # Список изменений цвета
        self.selection_mode = None  # 'delete', 'color', 'remove', 'eyedropper' или 'insert'
        self.start_x = None
        self.start_y = None
        self.target_color = "#0000FF"   # Синий по умолчанию
        self.eyedropper_color = None  # Цвет, выбранный пипеткой
        self.color_replacements = []  # Замены цвета для всей страницы (цвет -> цвет)
        self.color_tolerance = 30  # Допуск для поиска похожих цветов (0-255)
        self.inserted_content = []  # Вставленный контент: [{'page': int, 'type': 'text'/'image', 'x': float, 'y': float, 'data': {...}}]
        self.page_images = []  # Кэш базовых изображений страниц (без изменений)
        self.preview_images = {}  # Кэш изображений с примененными изменениями
        self.rect_id = None  # ID текущего прямоугольника выделения
        self.img_id = None  # ID изображения на canvas
        self.selection_rects = {}  # Словарь для хранения ID прямоугольников выделения
        self.show_preview = True  # Показывать предпросмотр изменений в реальном времени
        self.scroll_start_x = None  # Начальная позиция для прокрутки перетаскиванием
        self.scroll_start_y = None
        
        # Создание интерфейса
        self.create_widgets()
        # Привязка горячих клавиш
        self.bind_hotkeys()
    
    def create_menu(self):
        """Создание меню приложения"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Загрузить PDF...", command=self.load_pdf, accelerator="Ctrl+O")
        file_menu.add_command(label="Сохранить PDF...", command=self.save_pdf, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Сохранить шаблон...", command=self.save_template)
        file_menu.add_command(label="Загрузить шаблон...", command=self.load_template)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.on_closing, accelerator="Ctrl+Q")
        
        # Меню "Инструменты"
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Инструменты", menu=tools_menu)
        tools_menu.add_command(label="Выделить для удаления", 
                              command=lambda: self.set_selection_mode('delete'), 
                              accelerator="D")
        tools_menu.add_command(label="Выделить для замены цвета", 
                              command=lambda: self.set_selection_mode('color'), 
                              accelerator="C")
        tools_menu.add_command(label="Пипетка (замена цвета)", 
                              command=lambda: self.set_selection_mode('eyedropper'), 
                              accelerator="E")
        tools_menu.add_command(label="Удалить элемент", 
                              command=lambda: self.set_selection_mode('remove'), 
                              accelerator="R")
        tools_menu.add_command(label="Вставить контент", 
                              command=lambda: self.set_selection_mode('insert'), 
                              accelerator="I")
        tools_menu.add_separator()
        tools_menu.add_command(label="Очистить выделения", 
                              command=self.clear_selections, 
                              accelerator="Ctrl+X")
        tools_menu.add_command(label="Применить на страницах...", 
                              command=self.apply_to_pages, 
                              accelerator="Ctrl+A")
        
        # Меню "Вид"
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Увеличить", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Уменьшить", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Сброс масштаба", command=self.reset_zoom, accelerator="Ctrl+0")
        view_menu.add_separator()
        view_menu.add_command(label="Предыдущая страница", command=self.prev_page, accelerator="←")
        view_menu.add_command(label="Следующая страница", command=self.next_page, accelerator="→")
        
        # Меню "Справка"
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)
        help_menu.add_command(label="Горячие клавиши", command=self.show_hotkeys)
    
    def bind_hotkeys(self):
        """Привязка горячих клавиш"""
        # Файл
        self.root.bind('<Control-o>', lambda e: self.load_pdf())
        self.root.bind('<Control-O>', lambda e: self.load_pdf())
        self.root.bind('<Control-s>', lambda e: self.save_pdf())
        self.root.bind('<Control-S>', lambda e: self.save_pdf())
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<Control-Q>', lambda e: self.on_closing())
        
        # Инструменты
        self.root.bind('<KeyPress-d>', lambda e: self.set_selection_mode('delete') if self.pdf_document else None)
        self.root.bind('<KeyPress-D>', lambda e: self.set_selection_mode('delete') if self.pdf_document else None)
        self.root.bind('<KeyPress-c>', lambda e: self.set_selection_mode('color') if self.pdf_document else None)
        self.root.bind('<KeyPress-C>', lambda e: self.set_selection_mode('color') if self.pdf_document else None)
        self.root.bind('<KeyPress-e>', lambda e: self.set_selection_mode('eyedropper') if self.pdf_document else None)
        self.root.bind('<KeyPress-E>', lambda e: self.set_selection_mode('eyedropper') if self.pdf_document else None)
        self.root.bind('<KeyPress-r>', lambda e: self.set_selection_mode('remove') if self.pdf_document else None)
        self.root.bind('<KeyPress-R>', lambda e: self.set_selection_mode('remove') if self.pdf_document else None)
        self.root.bind('<KeyPress-i>', lambda e: self.set_selection_mode('insert') if self.pdf_document else None)
        self.root.bind('<KeyPress-I>', lambda e: self.set_selection_mode('insert') if self.pdf_document else None)
        self.root.bind('<Control-x>', lambda e: self.clear_selections() if self.pdf_document else None)
        self.root.bind('<Control-X>', lambda e: self.clear_selections() if self.pdf_document else None)
        self.root.bind('<Control-a>', lambda e: self.apply_to_pages() if self.pdf_document else None)
        self.root.bind('<Control-A>', lambda e: self.apply_to_pages() if self.pdf_document else None)
        
        # Вид
        self.root.bind('<Control-plus>', lambda e: self.zoom_in() if self.pdf_document else None)
        self.root.bind('<Control-equal>', lambda e: self.zoom_in() if self.pdf_document else None)
        self.root.bind('<Control-minus>', lambda e: self.zoom_out() if self.pdf_document else None)
        self.root.bind('<Control-0>', lambda e: self.reset_zoom() if self.pdf_document else None)
        self.root.bind('<Left>', lambda e: self.prev_page() if self.pdf_document else None)
        self.root.bind('<Right>', lambda e: self.next_page() if self.pdf_document else None)
        self.root.bind('<Prior>', lambda e: self.prev_page() if self.pdf_document else None)  # Page Up
        self.root.bind('<Next>', lambda e: self.next_page() if self.pdf_document else None)  # Page Down
        
        # Удаление элементов (Delete key)
        self.root.bind('<Delete>', lambda e: self.delete_selected_deletion() if self.pdf_document else None)
        self.root.bind('<BackSpace>', lambda e: self.delete_selected_color() if self.pdf_document else None)
        
    def show_about(self):
        """Показать информацию о программе"""
        about_text = """PDF Editor - Редактор PDF

Версия 1.0

Графическое приложение для редактирования PDF файлов:
• Удаление областей
• Замена цветов
• Применение изменений на нескольких страницах

© 2024"""
        messagebox.showinfo("О программе", about_text)
    
    def show_hotkeys(self):
        """Показать список горячих клавиш"""
        hotkeys_text = """ГОРЯЧИЕ КЛАВИШИ

Файл:
  Ctrl+O  - Загрузить PDF
  Ctrl+S  - Сохранить PDF
  Ctrl+Q  - Выход

Инструменты:
  D       - Выделить для удаления
  C       - Выделить для замены цвета
  E       - Пипетка (замена цвета)
  R       - Удалить элемент
  I       - Вставить контент
  Ctrl+X  - Очистить выделения
  Ctrl+A  - Применить на страницах

Вид:
  Ctrl++  - Увеличить масштаб
  Ctrl+-  - Уменьшить масштаб
  Ctrl+0  - Сброс масштаба
  ←       - Предыдущая страница
  →       - Следующая страница
  Page Up - Предыдущая страница
  Page Down - Следующая страница

Удаление:
  Delete  - Удалить выбранное (области)
  Backspace - Удалить выбранное (цвета)"""
        messagebox.showinfo("Горячие клавиши", hotkeys_text)
        
    def create_widgets(self):
        # Создание меню
        self.create_menu()
        
        # Панель инструментов
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Кнопки загрузки и сохранения
        load_btn = ttk.Button(toolbar, text="📂 Загрузить", command=self.load_pdf)
        load_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(load_btn, "Загрузить PDF файл (Ctrl+O)")
        
        save_btn = ttk.Button(toolbar, text="💾 Сохранить", command=self.save_pdf)
        save_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(save_btn, "Сохранить PDF файл (Ctrl+S)")
        
        # Разделитель
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10)
        
        # Шаблоны
        ttk.Label(toolbar, text="Шаблоны:").pack(side=tk.LEFT, padx=2)
        save_template_btn = ttk.Button(toolbar, text="💾 Сохранить шаблон", 
                                      command=self.save_template)
        save_template_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(save_template_btn, "Сохранить текущие выделения как шаблон")
        
        load_template_btn = ttk.Button(toolbar, text="📂 Загрузить шаблон", 
                                      command=self.load_template)
        load_template_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(load_template_btn, "Загрузить шаблон выделений")
        
        # Разделитель
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10)
        
        # Инструменты выделения
        ttk.Label(toolbar, text="Инструменты:").pack(side=tk.LEFT, padx=2)
        
        delete_btn = ttk.Button(toolbar, text="🗑️ Удаление", 
                  command=lambda: self.set_selection_mode('delete'))
        delete_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(delete_btn, "Выделить область для удаления (D)")
        
        color_btn = ttk.Button(toolbar, text="🎨 Замена цвета", 
                  command=lambda: self.set_selection_mode('color'))
        color_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(color_btn, "Выделить область для замены цвета (C)")
        
        eyedropper_btn = ttk.Button(toolbar, text="💧 Пипетка", 
                  command=lambda: self.set_selection_mode('eyedropper'))
        eyedropper_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(eyedropper_btn, "Выбрать цвет для замены на всей странице (E)")
        
        remove_btn = ttk.Button(toolbar, text="✂️ Удалить", 
                  command=lambda: self.set_selection_mode('remove'))
        remove_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(remove_btn, "Удалить выделенный элемент (R)")
        
        clear_btn = ttk.Button(toolbar, text="🧹 Очистить", 
                  command=self.clear_selections)
        clear_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(clear_btn, "Очистить все выделения на странице (Ctrl+X)")
        
        apply_btn = ttk.Button(toolbar, text="📋 Применить", 
                  command=self.apply_to_pages)
        apply_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(apply_btn, "Применить изменения на других страницах (Ctrl+A)")
        
        apply_all_colors_btn = ttk.Button(toolbar, text="🎨 Ко всем", 
                  command=self.apply_colors_to_all_pages)
        apply_all_colors_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(apply_all_colors_btn, "Применить замены цвета ко всем страницам")
        
        # Разделитель
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10)
        
        insert_btn = ttk.Button(toolbar, text="➕ Вставить", 
                  command=lambda: self.set_selection_mode('insert'))
        insert_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(insert_btn, "Вставить текст или изображение (I)")
        
        # Настройки цвета
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10)
        
        ttk.Label(toolbar, text="Цвет замены:").pack(side=tk.LEFT, padx=2)
        self.color_btn = tk.Button(toolbar, bg=self.target_color, width=4, height=1,
                                  command=self.choose_target_color, relief=tk.RAISED, 
                                  borderwidth=2, cursor="hand2")
        self.color_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(self.color_btn, "Выбрать цвет для замены")
        
        # Навигация по страницам
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10)
        
        prev_btn = ttk.Button(toolbar, text="◀ Назад", command=self.prev_page)
        prev_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(prev_btn, "Предыдущая страница (← или Page Up)")
        
        self.page_label = ttk.Label(toolbar, text="Страница: 0/0", font=("Arial", 9, "bold"))
        self.page_label.pack(side=tk.LEFT, padx=5)
        
        next_btn = ttk.Button(toolbar, text="Вперед ▶", command=self.next_page)
        next_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(next_btn, "Следующая страница (→ или Page Down)")
        
        # Масштаб
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10)
        ttk.Label(toolbar, text="Масштаб:").pack(side=tk.LEFT, padx=2)
        
        zoom_in_btn = ttk.Button(toolbar, text="🔍+", command=self.zoom_in)
        zoom_in_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(zoom_in_btn, "Увеличить масштаб (Ctrl++)")
        
        zoom_out_btn = ttk.Button(toolbar, text="🔍-", command=self.zoom_out)
        zoom_out_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(zoom_out_btn, "Уменьшить масштаб (Ctrl+-)")
        
        reset_zoom_btn = ttk.Button(toolbar, text="⟲ Сброс", command=self.reset_zoom)
        reset_zoom_btn.pack(side=tk.LEFT, padx=2)
        self.create_tooltip(reset_zoom_btn, "Сбросить масштаб (Ctrl+0)")
        
        # Основная область
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Панель предпросмотра
        self.preview_frame = ttk.LabelFrame(main_frame, text="Предпросмотр")
        self.preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Canvas с прокруткой для отображения PDF
        canvas_frame = ttk.Frame(self.preview_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='white')
        scrollbar_v = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar_h = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=scrollbar_v.set, xscrollcommand=scrollbar_h.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar_v.grid(row=0, column=1, sticky="ns")
        scrollbar_h.grid(row=1, column=0, sticky="ew")
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Привязка событий мыши
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Прокрутка перетаскиванием правой кнопкой мыши или средней кнопкой
        self.canvas.bind("<ButtonPress-2>", self.on_scroll_start)  # Средняя кнопка
        self.canvas.bind("<ButtonPress-3>", self.on_scroll_start)  # Правая кнопка
        self.canvas.bind("<B2-Motion>", self.on_scroll_drag)
        self.canvas.bind("<B3-Motion>", self.on_scroll_drag)
        self.canvas.bind("<ButtonRelease-2>", self.on_scroll_end)
        self.canvas.bind("<ButtonRelease-3>", self.on_scroll_end)
        
        # Привязка событий прокрутки к canvas и canvas_frame
        def on_mousewheel(event):
            """Обработка прокрутки колесика мыши"""
            if self.pdf_document:
                # Прокрутка по вертикали
                if event.delta:
                    delta = event.delta
                else:
                    delta = event.num == 4 and 1 or -1
                
                if delta > 0:
                    self.canvas.yview_scroll(-1, "units")
                else:
                    self.canvas.yview_scroll(1, "units")
        
        def on_mousewheel_shift(event):
            """Обработка прокрутки с Shift (горизонтальная)"""
            if self.pdf_document:
                if event.delta:
                    delta = event.delta
                else:
                    delta = event.num == 4 and 1 or -1
                
                if delta > 0:
                    self.canvas.xview_scroll(-1, "units")
                else:
                    self.canvas.xview_scroll(1, "units")
        
        # Привязка прокрутки к canvas
        self.canvas.bind("<MouseWheel>", on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", on_mousewheel_shift)
        # Поддержка прокрутки для Linux
        self.canvas.bind("<Button-4>", on_mousewheel)
        self.canvas.bind("<Button-5>", on_mousewheel)
        
        # Привязка прокрутки к canvas_frame (для работы когда курсор над фреймом)
        canvas_frame.bind("<MouseWheel>", on_mousewheel)
        canvas_frame.bind("<Shift-MouseWheel>", on_mousewheel_shift)
        canvas_frame.bind("<Button-4>", on_mousewheel)
        canvas_frame.bind("<Button-5>", on_mousewheel)
        
        # Привязка прокрутки для масштабирования (Ctrl+колесико)
        def on_mousewheel_zoom(event):
            """Обработка прокрутки с Ctrl (масштабирование)"""
            if self.pdf_document:
                if event.delta:
                    delta = event.delta
                else:
                    delta = event.num == 4 and 1 or -1
                
                if delta > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
        
        self.canvas.bind("<Control-MouseWheel>", on_mousewheel_zoom)
        canvas_frame.bind("<Control-MouseWheel>", on_mousewheel_zoom)
        
        # Установка фокуса на canvas для работы клавиатуры
        self.canvas.focus_set()
        
        # Привязка клавиш для прокрутки canvas
        def on_canvas_focus_in(event):
            """Canvas получил фокус"""
            self.canvas.focus_set()
        
        self.canvas.bind("<FocusIn>", on_canvas_focus_in)
        # Не привязываем Button-1 здесь, так как он используется для выделения
        # Фокус будет устанавливаться в on_mouse_down при необходимости
        
        # Привязка клавиш для прокрутки (когда canvas в фокусе)
        def scroll_up(event):
            if self.canvas.focus_get() == self.canvas:
                self.canvas.yview_scroll(-1, "units")
                return "break"
        
        def scroll_down(event):
            if self.canvas.focus_get() == self.canvas:
                self.canvas.yview_scroll(1, "units")
                return "break"
        
        def scroll_page_up(event):
            if self.canvas.focus_get() == self.canvas:
                self.canvas.yview_scroll(-1, "pages")
                return "break"
        
        def scroll_page_down(event):
            if self.canvas.focus_get() == self.canvas:
                self.canvas.yview_scroll(1, "pages")
                return "break"
        
        # Привязка клавиш прокрутки (только когда canvas в фокусе)
        self.canvas.bind("<Up>", scroll_up)
        self.canvas.bind("<Down>", scroll_down)
        # Page Up/Down используются для навигации по страницам, но также прокручивают canvas
        self.canvas.bind("<Home>", lambda e: (self.canvas.xview_moveto(0), self.canvas.yview_moveto(0), "break")[2] if self.canvas.focus_get() == self.canvas else None)
        self.canvas.bind("<End>", lambda e: (self.canvas.xview_moveto(1), self.canvas.yview_moveto(1), "break")[2] if self.canvas.focus_get() == self.canvas else None)
        
        # Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Панель информации
        info_frame = ttk.LabelFrame(main_frame, text="Информация", width=300)
        info_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        info_frame.pack_propagate(False)
        
        # Список областей для удаления
        deletion_frame = ttk.LabelFrame(info_frame, text="🗑️ Области для удаления")
        deletion_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.deletion_listbox = tk.Listbox(deletion_frame, height=6, font=("Arial", 9))
        self.deletion_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.deletion_listbox.bind("<Double-Button-1>", self.delete_selected_deletion)
        self.deletion_listbox.bind("<Delete>", lambda e: self.delete_selected_deletion())
        
        deletion_btn_frame = ttk.Frame(deletion_frame)
        deletion_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(deletion_btn_frame, text="Удалить", 
                  command=self.delete_selected_deletion).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.create_tooltip(deletion_btn_frame.winfo_children()[0], "Удалить выбранную область (Delete)")
        
        # Список замен цвета
        color_frame = ttk.LabelFrame(info_frame, text="🎨 Замены цвета")
        color_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.color_listbox = tk.Listbox(color_frame, height=6, font=("Arial", 9))
        self.color_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.color_listbox.bind("<Double-Button-1>", self.delete_selected_color)
        self.color_listbox.bind("<BackSpace>", lambda e: self.delete_selected_color())
        
        color_btn_frame = ttk.Frame(color_frame)
        color_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(color_btn_frame, text="Удалить", 
                  command=self.delete_selected_color).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.create_tooltip(color_btn_frame.winfo_children()[0], "Удалить выбранную замену (Backspace)")
        
        # Информация о выделении
        status_frame = ttk.LabelFrame(info_frame, text="📊 Статус")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.selection_info = ttk.Label(status_frame, text="Режим: Не выбран", 
                                        font=("Arial", 9, "bold"))
        self.selection_info.pack(anchor=tk.W, padx=5, pady=5)
        
        # Статусная строка внизу
        statusbar = ttk.Frame(self.root)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_label = ttk.Label(statusbar, text="Готов к работе", 
                                      relief=tk.SUNKEN, anchor=tk.W, font=("Arial", 8))
        self.status_label.pack(fill=tk.X, padx=2, pady=2)
    
    def create_tooltip(self, widget, text):
        """Создание подсказки для виджета"""
        def on_enter(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tooltip, text=text, background="#ffffe0", 
                           relief=tk.SOLID, borderwidth=1, font=("Arial", 8))
            label.pack()
            widget.tooltip = tooltip
        
        def on_leave(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)
        
    def load_pdf(self):
        """Загрузка PDF файла"""
        file_path = filedialog.askopenfilename(
            title="Выберите PDF файл",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                # Закрываем предыдущий документ, если он был открыт
                if self.pdf_document is not None:
                    self.pdf_document.close()
                
                self.pdf_document = fitz.open(file_path)
                self.total_pages = len(self.pdf_document)
                if self.total_pages == 0:
                    messagebox.showerror("Ошибка", "PDF файл не содержит страниц")
                    self.pdf_document.close()
                    self.pdf_document = None
                    return
                
                self.current_page = 0
                self.zoom = 1.0
                self.page_images = [None] * self.total_pages
                self.deletion_areas = [[] for _ in range(self.total_pages)]
                self.color_changes = [[] for _ in range(self.total_pages)]
                self.color_replacements = [[] for _ in range(self.total_pages)]
                self.inserted_content = []  # Очистка вставленного контента
                self.preview_images.clear()  # Очистка кэша предпросмотра
                self.update_page_display()
                self.update_info_panels()
                self.status_label.config(text=f"Загружен: {Path(file_path).name} ({self.total_pages} страниц)")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить PDF: {str(e)}")
                if self.pdf_document is not None:
                    self.pdf_document.close()
                    self.pdf_document = None
    
    def render_page(self, page_num, zoom=1.0, apply_changes=False):
        """Рендеринг страницы PDF в изображение"""
        if self.pdf_document is None or page_num >= self.total_pages:
            return None
            
        page = self.pdf_document[page_num]
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        img_data = pix.tobytes("ppm")
        img = Image.open(io.BytesIO(img_data))
        
        # Применение изменений в реальном времени
        if apply_changes:
            img = self.apply_changes_to_image(img, page_num, zoom)
        
        return ImageTk.PhotoImage(img)
    
    def apply_changes_to_image(self, img, page_num, zoom):
        """Применение изменений к изображению для предпросмотра"""
        from PIL import ImageDraw
        
        if page_num >= len(self.deletion_areas) and page_num >= len(self.color_changes):
            return img
        
        # Создаем копию изображения для редактирования
        img_copy = img.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Применение удалений (закрашивание белым)
        if page_num < len(self.deletion_areas):
            for area in self.deletion_areas[page_num]:
                x1, y1, x2, y2 = area
                # Масштабируем координаты
                x1_scaled = int(x1 * zoom)
                y1_scaled = int(y1 * zoom)
                x2_scaled = int(x2 * zoom)
                y2_scaled = int(y2 * zoom)
                
                # Ограничиваем координаты размерами изображения
                x1_scaled = max(0, min(x1_scaled, img.width))
                y1_scaled = max(0, min(y1_scaled, img.height))
                x2_scaled = max(0, min(x2_scaled, img.width))
                y2_scaled = max(0, min(y2_scaled, img.height))
                
                if x1_scaled < x2_scaled and y1_scaled < y2_scaled:
                    draw.rectangle([x1_scaled, y1_scaled, x2_scaled, y2_scaled], 
                                 fill=(255, 255, 255), outline=None)
        
        # Применение замены цвета
        if page_num < len(self.color_changes):
            for change in self.color_changes[page_num]:
                area, orig_color, new_color = change
                x1, y1, x2, y2 = area
                # Масштабируем координаты
                x1_scaled = int(x1 * zoom)
                y1_scaled = int(y1 * zoom)
                x2_scaled = int(x2 * zoom)
                y2_scaled = int(y2 * zoom)
                
                # Ограничиваем координаты размерами изображения
                x1_scaled = max(0, min(x1_scaled, img.width))
                y1_scaled = max(0, min(y1_scaled, img.height))
                x2_scaled = max(0, min(x2_scaled, img.width))
                y2_scaled = max(0, min(y2_scaled, img.height))
                
                if x1_scaled < x2_scaled and y1_scaled < y2_scaled:
                    # Конвертация hex цвета в RGB
                    if new_color and new_color.startswith('#'):
                        try:
                            r = int(new_color[1:3], 16)
                            g = int(new_color[3:5], 16)
                            b = int(new_color[5:7], 16)
                            draw.rectangle([x1_scaled, y1_scaled, x2_scaled, y2_scaled], 
                                         fill=(r, g, b), outline=None)
                        except (ValueError, IndexError):
                            pass
        
        # Применение замены цвета на всей странице (пипетка)
        if page_num < len(self.color_replacements) and self.color_replacements[page_num]:
            # Используем PIL для замены цвета (без numpy для совместимости)
            pixels = img_copy.load()
            width, height = img_copy.size
            
            for replacement in self.color_replacements[page_num]:
                old_color_hex = replacement['old_color']
                new_color_hex = replacement['new_color']
                tolerance = replacement.get('tolerance', self.color_tolerance)
                
                # Конвертируем hex цвета в RGB
                try:
                    old_r = int(old_color_hex[1:3], 16)
                    old_g = int(old_color_hex[3:5], 16)
                    old_b = int(old_color_hex[5:7], 16)
                    
                    new_r = int(new_color_hex[1:3], 16)
                    new_g = int(new_color_hex[3:5], 16)
                    new_b = int(new_color_hex[5:7], 16)
                except (ValueError, IndexError):
                    continue
                
                # Проходим по всем пикселям и заменяем похожие цвета
                for y in range(height):
                    for x in range(width):
                        r, g, b = pixels[x, y]
                        
                        # Вычисляем расстояние между цветами (евклидово расстояние)
                        color_distance = ((r - old_r)**2 + (g - old_g)**2 + (b - old_b)**2)**0.5
                        
                        # Если цвет в пределах допуска, заменяем его
                        if color_distance <= tolerance:
                            pixels[x, y] = (new_r, new_g, new_b)
        
        # Применение вставленного контента
        for content in self.inserted_content:
            if content['page'] == page_num:
                x = int(content['x'] * zoom)
                y = int(content['y'] * zoom)
                
                if content['type'] == 'text':
                    # Вставляем текст
                    try:
                        from PIL import ImageFont
                        text = content['data']['text']
                        font_size = content['data']['font_size']
                        color_hex = content['data']['color']
                        
                        # Конвертируем цвет
                        r = int(color_hex[1:3], 16)
                        g = int(color_hex[3:5], 16)
                        b = int(color_hex[5:7], 16)
                        
                        # Пытаемся загрузить шрифт, если не получается - используем стандартный
                        try:
                            font = ImageFont.truetype("arial.ttf", font_size)
                        except:
                            try:
                                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                            except:
                                font = ImageFont.load_default()
                        
                        # Рисуем текст
                        draw.text((x, y), text, fill=(r, g, b), font=font)
                    except Exception as e:
                        # Если не удалось вставить текст, просто пропускаем
                        pass
                
                elif content['type'] == 'image':
                    # Вставляем изображение
                    try:
                        img_path = content['data']['path']
                        if Path(img_path).exists():
                            insert_img = Image.open(img_path)
                            
                            # Изменяем размер, если нужно
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
                            
                            # Вставляем изображение
                            img_copy.paste(insert_img, (x, y), insert_img if insert_img.mode == 'RGBA' else None)
                    except Exception as e:
                        # Если не удалось вставить изображение, просто пропускаем
                        pass
        
        return img_copy
    
    def update_page_display(self):
        """Обновление отображения текущей страницы"""
        if self.pdf_document is None or not (0 <= self.current_page < self.total_pages):
            return
            
        # Очистка canvas
        self.canvas.delete("all")
        self.img_id = None
        
        # Рендеринг базового изображения страницы (кэшируется)
        if self.page_images[self.current_page] is None:
            self.page_images[self.current_page] = self.render_page(self.current_page, self.zoom, apply_changes=False)
        
        if self.page_images[self.current_page] is None:
            return
        
        # Определяем, какое изображение показывать
        page_key = f"{self.current_page}_{self.zoom}"
        display_image = None
        
        if self.show_preview:
            # Проверяем, есть ли изменения для этой страницы
            has_changes = (
                (self.current_page < len(self.deletion_areas) and len(self.deletion_areas[self.current_page]) > 0) or
                (self.current_page < len(self.color_changes) and len(self.color_changes[self.current_page]) > 0) or
                (self.current_page < len(self.color_replacements) and len(self.color_replacements[self.current_page]) > 0) or
                any(c['page'] == self.current_page for c in self.inserted_content)
            )
            
            if has_changes:
                # Создаем изображение с примененными изменениями
                if page_key not in self.preview_images:
                    # Получаем базовое изображение
                    base_img = self.render_page(self.current_page, self.zoom, apply_changes=False)
                    if base_img:
                        # Конвертируем PhotoImage обратно в PIL Image для редактирования
                        page = self.pdf_document[self.current_page]
                        mat = fitz.Matrix(self.zoom, self.zoom)
                        pix = page.get_pixmap(matrix=mat, alpha=False)
                        img_data = pix.tobytes("ppm")
                        img = Image.open(io.BytesIO(img_data))
                        # Применяем изменения
                        img_with_changes = self.apply_changes_to_image(img, self.current_page, self.zoom)
                        self.preview_images[page_key] = ImageTk.PhotoImage(img_with_changes)
                display_image = self.preview_images.get(page_key)
            else:
                # Нет изменений, используем базовое изображение
                display_image = self.page_images[self.current_page]
        else:
            # Режим без предпросмотра
            display_image = self.page_images[self.current_page]
        
        if display_image is None:
            display_image = self.page_images[self.current_page]
        
        # Получение размеров изображения
        img_width = display_image.width()
        img_height = display_image.height()
        
        # Отображение страницы
        self.img_id = self.canvas.create_image(
            20, 20, 
            anchor=tk.NW, 
            image=display_image
        )
        
        # Установка области прокрутки
        self.canvas.config(scrollregion=(0, 0, img_width + 40, img_height + 40))
        
        # Отображение контуров выделенных областей (для навигации)
        # В режиме предпросмотра показываем тонкие контуры поверх изображения
        self.draw_selection_areas()
        
        # Обновление метки страницы
        self.page_label.config(text=f"Страница: {self.current_page + 1}/{self.total_pages}")
        
        # Обновление информации о выделениях для текущей страницы
        self.update_info_panels()
    
    def draw_selection_areas(self):
        """Отрисовка выделенных областей на canvas"""
        if not (0 <= self.current_page < len(self.deletion_areas)):
            return
        
        # Очистка словаря для текущей страницы
        page_key = f"page_{self.current_page}"
        self.selection_rects[page_key] = {'delete': [], 'color': []}
            
        # Области для удаления (красные прямоугольники)
        for idx, area in enumerate(self.deletion_areas[self.current_page]):
            x1, y1, x2, y2 = area
            rect_id = self.canvas.create_rectangle(
                x1 * self.zoom + 20, y1 * self.zoom + 20,
                x2 * self.zoom + 20, y2 * self.zoom + 20,
                outline='red', width=2, dash=(5, 5),
                tags=("delete_area", f"delete_{idx}")
            )
            self.selection_rects[page_key]['delete'].append((rect_id, idx))
        
        # Области для замены цвета (синие прямоугольники)
        if self.current_page < len(self.color_changes):
            for idx, change in enumerate(self.color_changes[self.current_page]):
                area, orig_color, new_color = change
                x1, y1, x2, y2 = area
                rect_id = self.canvas.create_rectangle(
                    x1 * self.zoom + 20, y1 * self.zoom + 20,
                    x2 * self.zoom + 20, y2 * self.zoom + 20,
                    outline='blue', width=2, dash=(2, 2),
                    tags=("color_area", f"color_{idx}")
                )
                self.selection_rects[page_key]['color'].append((rect_id, idx))
        
        # Отображение вставленного контента
        for idx, content in enumerate(self.inserted_content):
            if content['page'] == self.current_page:
                x = content['x'] * self.zoom + 20
                y = content['y'] * self.zoom + 20
                
                if content['type'] == 'text':
                    # Отображаем маркер для текста
                    self.canvas.create_text(
                        x, y,
                        text="T",
                        fill='green',
                        font=("Arial", 12, "bold"),
                        tags=("inserted_content", f"content_{idx}")
                    )
                    # Показываем текст рядом
                    text_preview = content['data']['text'][:20] + "..." if len(content['data']['text']) > 20 else content['data']['text']
                    self.canvas.create_text(
                        x + 15, y,
                        text=text_preview,
                        fill='green',
                        font=("Arial", 8),
                        anchor=tk.W,
                        tags=("inserted_content", f"content_{idx}")
                    )
                elif content['type'] == 'image':
                    # Отображаем маркер для изображения
                    self.canvas.create_rectangle(
                        x - 5, y - 5, x + 5, y + 5,
                        outline='green', fill='lightgreen', width=2,
                        tags=("inserted_content", f"content_{idx}")
                    )
                    # Показываем имя файла
                    img_name = Path(content['data']['path']).name
                    self.canvas.create_text(
                        x + 10, y,
                        text=img_name[:15] + "..." if len(img_name) > 15 else img_name,
                        fill='green',
                        font=("Arial", 8),
                        anchor=tk.W,
                        tags=("inserted_content", f"content_{idx}")
            )
    
    def on_mouse_down(self, event):
        """Начало выделения области или удаление элемента"""
        # Устанавливаем фокус на canvas для работы клавиатуры
        self.canvas.focus_set()
        
        if not self.pdf_document or not (0 <= self.current_page < self.total_pages):
            return
        
        # Режим пипетки для выбора цвета
        if self.selection_mode == 'eyedropper':
            # Получаем координаты в масштабе страницы
            page_x = (event.x - 20) / self.zoom
            page_y = (event.y - 20) / self.zoom
            
            # Получаем страницу PDF
            page = self.pdf_document[self.current_page]
            page_width = page.rect.width
            page_height = page.rect.height
            
            # Проверяем, что клик в пределах страницы
            if 0 <= page_x < page_width and 0 <= page_y < page_height:
                # Получаем изображение страницы
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Получаем цвет пикселя
                pixel_x = int(page_x)
                pixel_y = int(page_y)
                
                # Ограничиваем координаты
                pixel_x = max(0, min(pixel_x, img.width - 1))
                pixel_y = max(0, min(pixel_y, img.height - 1))
                
                # Получаем RGB цвет
                r, g, b = img.getpixel((pixel_x, pixel_y))
                selected_color = f"#{r:02x}{g:02x}{b:02x}"
                self.eyedropper_color = selected_color
                
                # Показываем диалог выбора нового цвета
                new_color = colorchooser.askcolor(
                    title="Выберите новый цвет для замены",
                    initialcolor=selected_color
                )
                
                if new_color and new_color[1]:
                    # Добавляем замену цвета для всей страницы
                    if self.current_page >= len(self.color_replacements):
                        while len(self.color_replacements) <= self.current_page:
                            self.color_replacements.append([])
                    
                    self.color_replacements[self.current_page].append({
                        'old_color': selected_color,
                        'new_color': new_color[1],
                        'tolerance': self.color_tolerance
                    })
                    
                    # Инвалидируем кэш предпросмотра
                    self.invalidate_preview_cache(self.current_page)
                    self.update_page_display()
                    self.update_info_panels()
            return
        
        # Режим удаления элементов по клику
        if self.selection_mode == 'remove':
            page_key = f"page_{self.current_page}"
            if page_key in self.selection_rects:
                # Находим ближайший элемент к точке клика
                clicked_items = self.canvas.find_closest(event.x, event.y)
                if clicked_items:
                    item_id = clicked_items[0]
                    tags = self.canvas.gettags(item_id)
                    
                    # Проверяем, что клик действительно внутри области
                    coords = self.canvas.coords(item_id)
                    if len(coords) >= 4:
                        x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]
                        # Нормализация координат (на случай, если они перевернуты)
                        x_min, x_max = min(x1, x2), max(x1, x2)
                        y_min, y_max = min(y1, y2), max(y1, y2)
                        if x_min <= event.x <= x_max and y_min <= event.y <= y_max:
                            if 'delete_area' in tags:
                                # Находим индекс области
                                for rect_id, idx in self.selection_rects[page_key]['delete']:
                                    if rect_id == item_id and 0 <= idx < len(self.deletion_areas[self.current_page]):
                                        del self.deletion_areas[self.current_page][idx]
                                        self.invalidate_preview_cache(self.current_page)
                                        self.update_page_display()
                                        self.update_info_panels()
                                        return
                            elif 'color_area' in tags:
                                # Находим индекс замены цвета
                                for rect_id, idx in self.selection_rects[page_key]['color']:
                                    if rect_id == item_id and 0 <= idx < len(self.color_changes[self.current_page]):
                                        del self.color_changes[self.current_page][idx]
                                        self.invalidate_preview_cache(self.current_page)
                                        self.update_page_display()
                                        self.update_info_panels()
                                        return
                            elif 'inserted_content' in tags:
                                # Находим индекс вставленного контента
                                for tag in tags:
                                    if tag.startswith('content_'):
                                        idx = int(tag.split('_')[1])
                                        if 0 <= idx < len(self.inserted_content):
                                            if self.inserted_content[idx]['page'] == self.current_page:
                                                del self.inserted_content[idx]
                                                self.invalidate_preview_cache(self.current_page)
                                                self.update_page_display()
                                                self.update_info_panels()
                                                return
            return
        
        # Режим вставки контента
        if self.selection_mode == 'insert':
            # Получаем координаты в масштабе страницы
            page_x = (event.x - 20) / self.zoom
            page_y = (event.y - 20) / self.zoom
            
            # Получаем страницу PDF
            page = self.pdf_document[self.current_page]
            page_width = page.rect.width
            page_height = page.rect.height
            
            # Проверяем, что клик в пределах страницы
            if 0 <= page_x < page_width and 0 <= page_y < page_height:
                self.show_insert_dialog(page_x, page_y)
            return
        
        # Режимы выделения
        if self.selection_mode in ('delete', 'color'):
            self.start_x = (event.x - 20) / self.zoom
            self.start_y = (event.y - 20) / self.zoom
            
            # Удаляем предыдущий прямоугольник, если он есть
            if self.rect_id is not None:
                self.canvas.delete(self.rect_id)
            
            self.rect_id = self.canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline='green' if self.selection_mode == 'delete' else 'blue',
                width=2
            )
    
    def on_mouse_drag(self, event):
        """Изменение размера выделенной области"""
        if (self.selection_mode in ('delete', 'color') and 
            self.rect_id is not None and 
            self.start_x is not None and 
            self.start_y is not None):
            self.canvas.coords(self.rect_id, 
                              self.start_x * self.zoom + 20, 
                              self.start_y * self.zoom + 20,
                              event.x, event.y)
    
    def invalidate_preview_cache(self, page_num=None):
        """Инвалидация кэша предпросмотра для страницы"""
        if page_num is not None:
            # Удаляем все кэшированные изображения для этой страницы
            keys_to_remove = [k for k in self.preview_images.keys() if k.startswith(f"{page_num}_")]
            for key in keys_to_remove:
                del self.preview_images[key]
        else:
            # Очищаем весь кэш
            self.preview_images.clear()
    
    def on_mouse_up(self, event):
        """Завершение выделения области"""
        if (self.selection_mode not in ('delete', 'color') or
            self.rect_id is None or self.start_x is None or self.start_y is None or 
            self.pdf_document is None or 
            not (0 <= self.current_page < self.total_pages)):
            return
        
            end_x = (event.x - 20) / self.zoom
            end_y = (event.y - 20) / self.zoom
            
            # Нормализация координат
            x1 = min(self.start_x, end_x)
            y1 = min(self.start_y, end_y)
            x2 = max(self.start_x, end_x)
            y2 = max(self.start_y, end_y)
            
        # Проверка минимального размера области
        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
            self.start_x = None
            self.start_y = None
            return
        
        # Получение размеров страницы для валидации координат
        page = self.pdf_document[self.current_page]
        page_width = page.rect.width
        page_height = page.rect.height
        
        # Ограничение координат границами страницы
        x1 = max(0, min(x1, page_width))
        y1 = max(0, min(y1, page_height))
        x2 = max(0, min(x2, page_width))
        y2 = max(0, min(y2, page_height))
        
        # Проверка, что область не пустая после нормализации
        if x1 >= x2 or y1 >= y2:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
            self.start_x = None
            self.start_y = None
            return
        
        try:
            if self.selection_mode == 'delete':
                self.deletion_areas[self.current_page].append((x1, y1, x2, y2))
                # Инвалидируем кэш предпросмотра для текущей страницы
                self.invalidate_preview_cache(self.current_page)
            elif self.selection_mode == 'color':
                # Получение исходного цвета из PDF
                pix = page.get_pixmap()
                
                # Получение среднего цвета в области
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                # Ограничение координат для обрезки
                crop_x1 = max(0, int(x1))
                crop_y1 = max(0, int(y1))
                crop_x2 = min(pix.width, int(x2))
                crop_y2 = min(pix.height, int(y2))
                
                if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                    cropped = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                colors = cropped.getcolors(maxcolors=10000)
                
                if colors:
                    # Берем самый частый цвет
                    most_common = max(colors, key=lambda x: x[0])[1]
                    orig_color = '#%02x%02x%02x' % most_common
                    
                    self.color_changes[self.current_page].append(
                        ((x1, y1, x2, y2), orig_color, self.target_color)
                    )
                    # Инвалидируем кэш предпросмотра для текущей страницы
                    self.invalidate_preview_cache(self.current_page)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обработать выделение: {str(e)}")
            if self.rect_id:
                self.canvas.delete(self.rect_id)
        self.rect_id = None
        self.start_x = None
        self.start_y = None
        self.update_page_display()
    
    def on_mouse_wheel(self, event):
        """Обработка прокрутки колесика мыши"""
        if self.pdf_document:
            # Поддержка разных платформ (Windows/Mac использует delta, Linux - num)
            delta = event.delta if hasattr(event, 'delta') else (event.num == 4 and 1 or -1)
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
    
    def on_scroll_start(self, event):
        """Начало прокрутки перетаскиванием"""
        self.scroll_start_x = event.x
        self.scroll_start_y = event.y
        self.canvas.config(cursor="fleur")
    
    def on_scroll_drag(self, event):
        """Прокрутка перетаскиванием"""
        if self.scroll_start_x is not None and self.scroll_start_y is not None:
            # Вычисляем смещение
            dx = event.x - self.scroll_start_x
            dy = event.y - self.scroll_start_y
            
            # Прокручиваем canvas
            self.canvas.xview_scroll(int(-dx), "units")
            self.canvas.yview_scroll(int(-dy), "units")
            
            # Обновляем начальную позицию
            self.scroll_start_x = event.x
            self.scroll_start_y = event.y
    
    def on_scroll_end(self, event):
        """Конец прокрутки перетаскиванием"""
        self.scroll_start_x = None
        self.scroll_start_y = None
        self.canvas.config(cursor="")
    
    def set_selection_mode(self, mode):
        """Установка режима выделения"""
        self.selection_mode = mode
        if mode == 'delete':
            self.selection_info.config(text="Режим: Выделение для удаления")
            self.status_label.config(text="Режим: Выделение для удаления (D)")
        elif mode == 'color':
            self.selection_info.config(text="Режим: Замена цвета")
            self.status_label.config(text="Режим: Замена цвета (C)")
        elif mode == 'eyedropper':
            self.selection_info.config(text="Режим: Пипетка (кликните на цвет)")
            self.status_label.config(text="Режим: Пипетка - выберите цвет для замены (E)")
        elif mode == 'remove':
            self.selection_info.config(text="Режим: Удаление элемента")
            self.status_label.config(text="Режим: Удаление элемента (R)")
        elif mode == 'insert':
            self.selection_info.config(text="Режим: Вставка контента")
            self.status_label.config(text="Режим: Вставка контента - кликните на место вставки (I)")
        else:
            self.selection_info.config(text="Режим: Не выбран")
            self.status_label.config(text="Готов к работе")
    
    def choose_target_color(self):
        """Выбор целевого цвета для замены"""
        color = colorchooser.askcolor(title="Выберите цвет для замены", 
                                     initialcolor=self.target_color)
        if color and color[1]:
            self.target_color = color[1]
            self.color_btn.config(bg=self.target_color)
    
    def show_insert_dialog(self, x, y):
        """Диалог для вставки контента"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Вставить контент")
        dialog.geometry("450x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрируем окно
        dialog.update_idletasks()
        screen_x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        screen_y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{screen_x}+{screen_y}")
        
        ttk.Label(dialog, text=f"Позиция вставки: ({int(x)}, {int(y)})", 
                 font=("Arial", 9)).pack(padx=10, pady=10)
        
        # Выбор типа контента
        content_type_frame = ttk.LabelFrame(dialog, text="Тип контента")
        content_type_frame.pack(padx=10, pady=5, fill=tk.X)
        
        content_type = tk.StringVar(value="text")
        ttk.Radiobutton(content_type_frame, text="Текст", 
                       variable=content_type, value="text").pack(anchor=tk.W, padx=10, pady=5)
        ttk.Radiobutton(content_type_frame, text="Изображение", 
                       variable=content_type, value="image").pack(anchor=tk.W, padx=10, pady=5)
        
        # Фрейм для параметров текста
        text_frame = ttk.LabelFrame(dialog, text="Параметры текста")
        text_frame.pack(padx=10, pady=5, fill=tk.X)
        
        ttk.Label(text_frame, text="Текст:").pack(anchor=tk.W, padx=5, pady=2)
        text_entry = tk.Text(text_frame, height=4, width=40)
        text_entry.pack(padx=5, pady=2, fill=tk.X)
        text_entry.insert("1.0", "Введите текст...")
        
        ttk.Label(text_frame, text="Размер шрифта:").pack(anchor=tk.W, padx=5, pady=2)
        font_size_var = tk.StringVar(value="12")
        font_size_spin = ttk.Spinbox(text_frame, from_=6, to=72, textvariable=font_size_var, width=10)
        font_size_spin.pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Label(text_frame, text="Цвет текста:").pack(anchor=tk.W, padx=5, pady=2)
        text_color_frame = ttk.Frame(text_frame)
        text_color_frame.pack(anchor=tk.W, padx=5, pady=2)
        text_color_var = tk.StringVar(value="#000000")
        text_color_btn = tk.Button(text_color_frame, bg=text_color_var.get(), width=4, height=1,
                                  command=lambda: self.choose_text_color(text_color_var, text_color_btn))
        text_color_btn.pack(side=tk.LEFT, padx=2)
        
        # Фрейм для параметров изображения
        image_frame = ttk.LabelFrame(dialog, text="Параметры изображения")
        image_frame.pack(padx=10, pady=5, fill=tk.X)
        
        image_path_var = tk.StringVar(value="")
        ttk.Label(image_frame, text="Путь к изображению:").pack(anchor=tk.W, padx=5, pady=2)
        image_path_frame = ttk.Frame(image_frame)
        image_path_frame.pack(fill=tk.X, padx=5, pady=2)
        image_path_entry = ttk.Entry(image_path_frame, textvariable=image_path_var, width=30)
        image_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(image_path_frame, text="Обзор...", 
                  command=lambda: self.browse_image(image_path_var)).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(image_frame, text="Ширина (пиксели, 0 = оригинал):").pack(anchor=tk.W, padx=5, pady=2)
        image_width_var = tk.StringVar(value="0")
        ttk.Spinbox(image_frame, from_=0, to=2000, textvariable=image_width_var, width=10).pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Label(image_frame, text="Высота (пиксели, 0 = оригинал):").pack(anchor=tk.W, padx=5, pady=2)
        image_height_var = tk.StringVar(value="0")
        ttk.Spinbox(image_frame, from_=0, to=2000, textvariable=image_height_var, width=10).pack(anchor=tk.W, padx=5, pady=2)
        
        # Функция для переключения видимости фреймов
        def update_frames():
            if content_type.get() == "text":
                text_frame.pack(padx=10, pady=5, fill=tk.X)
                image_frame.pack_forget()
            else:
                text_frame.pack_forget()
                image_frame.pack(padx=10, pady=5, fill=tk.X)
        
        content_type.trace('w', lambda *args: update_frames())
        update_frames()
        
        # Кнопки
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(padx=10, pady=10)
        
        def insert_content():
            if content_type.get() == "text":
                text = text_entry.get("1.0", tk.END).strip()
                if not text or text == "Введите текст...":
                    messagebox.showwarning("Предупреждение", "Введите текст для вставки")
                    return
                
                try:
                    font_size = int(font_size_var.get())
                    text_color = text_color_var.get()
                    
                    # Добавляем контент
                    content_item = {
                        'page': self.current_page,
                        'type': 'text',
                        'x': x,
                        'y': y,
                        'data': {
                            'text': text,
                            'font_size': font_size,
                            'color': text_color
                        }
                    }
                    self.inserted_content.append(content_item)
                    
                    # Инвалидируем кэш
                    self.invalidate_preview_cache(self.current_page)
                    self.update_page_display()
                    self.update_info_panels()
                    
                    dialog.destroy()
                    messagebox.showinfo("Успех", "Текст добавлен для вставки")
                    
                except ValueError:
                    messagebox.showerror("Ошибка", "Неверный размер шрифта")
            else:
                image_path = image_path_var.get()
                if not image_path:
                    messagebox.showwarning("Предупреждение", "Выберите изображение")
                    return
                
                if not Path(image_path).exists():
                    messagebox.showerror("Ошибка", "Файл изображения не найден")
                    return
                
                try:
                    width = int(image_width_var.get()) if image_width_var.get() else 0
                    height = int(image_height_var.get()) if image_height_var.get() else 0
                    
                    # Добавляем контент
                    content_item = {
                        'page': self.current_page,
                        'type': 'image',
                        'x': x,
                        'y': y,
                        'data': {
                            'path': image_path,
                            'width': width,
                            'height': height
                        }
                    }
                    self.inserted_content.append(content_item)
                    
                    # Инвалидируем кэш
                    self.invalidate_preview_cache(self.current_page)
                    self.update_page_display()
                    self.update_info_panels()
                    
                    dialog.destroy()
                    messagebox.showinfo("Успех", "Изображение добавлено для вставки")
                    
                except ValueError:
                    messagebox.showerror("Ошибка", "Неверные размеры изображения")
        
        ttk.Button(buttons_frame, text="Вставить", command=insert_content).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def choose_text_color(self, color_var, btn):
        """Выбор цвета текста"""
        color = colorchooser.askcolor(title="Выберите цвет текста", 
                                     initialcolor=color_var.get())
        if color and color[1]:
            color_var.set(color[1])
            btn.config(bg=color[1])
    
    def browse_image(self, path_var):
        """Выбор файла изображения"""
        file_path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[
                ("Изображения", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("Все файлы", "*.*")
            ]
        )
        if file_path:
            path_var.set(file_path)
    
    def on_closing(self):
        """Обработка закрытия приложения"""
        if self.pdf_document is not None:
            self.pdf_document.close()
        self.root.destroy()
    
    def delete_selected_deletion(self, event=None):
        """Удаление выбранной области для удаления"""
        if (self.pdf_document is None or 
            not (0 <= self.current_page < len(self.deletion_areas))):
            return
        
        selection = self.deletion_listbox.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.deletion_areas[self.current_page]):
                del self.deletion_areas[self.current_page][index]
                self.invalidate_preview_cache(self.current_page)
                self.update_page_display()
                self.update_info_panels()
    
    def delete_selected_color(self, event=None):
        """Удаление выбранной замены цвета"""
        if (self.pdf_document is None or 
            not (0 <= self.current_page < len(self.color_changes))):
            return
        
        selection = self.color_listbox.curselection()
        if selection:
            index = selection[0]
            if 0 <= index < len(self.color_changes[self.current_page]):
                del self.color_changes[self.current_page][index]
                self.invalidate_preview_cache(self.current_page)
                self.update_page_display()
                self.update_info_panels()
    
    def clear_selections(self):
        """Очистка всех выделений на текущей странице"""
        if (self.pdf_document is None or 
            not (0 <= self.current_page < len(self.deletion_areas))):
            return
        
        self.deletion_areas[self.current_page] = []
        if self.current_page < len(self.color_changes):
            self.color_changes[self.current_page] = []
        if self.current_page < len(self.color_replacements):
            self.color_replacements[self.current_page] = []
        # Удаляем вставленный контент на текущей странице
        self.inserted_content = [c for c in self.inserted_content if c['page'] != self.current_page]
        self.invalidate_preview_cache(self.current_page)
        self.update_page_display()
        self.update_info_panels()
    
    def apply_to_pages(self):
        """Применение удалений и замен цвета с текущей страницы на выбранные страницы"""
        if self.pdf_document is None or self.total_pages == 0:
            messagebox.showwarning("Предупреждение", "Сначала загрузите PDF файл")
            return
        
        # Проверяем, есть ли что применять
        has_deletions = (self.current_page < len(self.deletion_areas) and 
                        len(self.deletion_areas[self.current_page]) > 0)
        has_color_changes = (self.current_page < len(self.color_changes) and 
                           len(self.color_changes[self.current_page]) > 0)
        has_color_replacements = (self.current_page < len(self.color_replacements) and 
                                 len(self.color_replacements[self.current_page]) > 0)
        has_inserted_content = any(c['page'] == self.current_page for c in self.inserted_content)
        
        if not has_deletions and not has_color_changes and not has_color_replacements and not has_inserted_content:
            messagebox.showinfo("Информация", "На текущей странице нет выделений для применения")
            return
        
        # Создаем диалог выбора страниц
        dialog = tk.Toplevel(self.root)
        dialog.title("Применить на страницах")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрируем окно
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Информация
        info_text = f"Текущая страница: {self.current_page + 1}\n"
        if has_deletions:
            info_text += f"Областей для удаления: {len(self.deletion_areas[self.current_page])}\n"
        if has_color_changes:
            info_text += f"Замен цвета (области): {len(self.color_changes[self.current_page])}\n"
        if has_color_replacements:
            info_text += f"Замен цвета (вся страница): {len(self.color_replacements[self.current_page])}\n"
        if has_inserted_content:
            content_count = sum(1 for c in self.inserted_content if c['page'] == self.current_page)
            info_text += f"Вставленный контент: {content_count}\n"
        
        ttk.Label(dialog, text=info_text).pack(padx=10, pady=10, anchor=tk.W)
        
        # Выбор типа изменений для применения
        changes_frame = ttk.LabelFrame(dialog, text="Тип изменений")
        changes_frame.pack(padx=10, pady=5, fill=tk.X)
        
        apply_deletions_var = tk.BooleanVar(value=has_deletions)
        apply_colors_var = tk.BooleanVar(value=has_color_changes)
        apply_color_replacements_var = tk.BooleanVar(value=has_color_replacements)
        apply_inserted_content_var = tk.BooleanVar(value=has_inserted_content)
        
        if has_deletions:
            ttk.Checkbutton(changes_frame, text="Применить удаления", 
                          variable=apply_deletions_var).pack(anchor=tk.W, padx=5, pady=2)
        if has_color_changes:
            ttk.Checkbutton(changes_frame, text="Применить замены цвета (области)", 
                          variable=apply_colors_var).pack(anchor=tk.W, padx=5, pady=2)
        if has_color_replacements:
            ttk.Checkbutton(changes_frame, text="Применить замены цвета (вся страница)", 
                          variable=apply_color_replacements_var).pack(anchor=tk.W, padx=5, pady=2)
        if has_inserted_content:
            ttk.Checkbutton(changes_frame, text="Применить вставленный контент", 
                          variable=apply_inserted_content_var).pack(anchor=tk.W, padx=5, pady=2)
        
        ttk.Label(dialog, text="Выберите страницы для применения:").pack(padx=10, pady=(10, 5), anchor=tk.W)
        
        # Фрейм с чекбоксами
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Canvas для чекбоксов
        canvas = tk.Canvas(frame, yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=canvas.yview)
        
        # Фрейм внутри canvas для чекбоксов
        checkboxes_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window(0, 0, anchor=tk.NW, window=checkboxes_frame)
        
        # Переменные для чекбоксов
        page_vars = {}
        checkboxes = []
        
        # Создаем чекбоксы для каждой страницы
        for page_num in range(self.total_pages):
            var = tk.BooleanVar()
            page_vars[page_num] = var
            
            # Не отмечаем текущую страницу (она уже имеет эти выделения)
            if page_num == self.current_page:
                var.set(False)
            else:
                var.set(False)
            
            checkbox = ttk.Checkbutton(
                checkboxes_frame, 
                text=f"Страница {page_num + 1}",
                variable=var
            )
            checkbox.pack(anchor=tk.W, padx=5, pady=2)
            checkboxes.append(checkbox)
        
        # Обновление размера canvas
        def update_canvas_size(event=None):
            canvas.update_idletasks()
            canvas.config(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())
        
        checkboxes_frame.bind('<Configure>', update_canvas_size)
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        # Кнопки "Выбрать все" и "Снять все"
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(padx=10, pady=5)
        
        def select_all():
            for page_num in range(self.total_pages):
                if page_num != self.current_page:
                    page_vars[page_num].set(True)
        
        def deselect_all():
            for var in page_vars.values():
                var.set(False)
        
        ttk.Button(buttons_frame, text="Выбрать все", command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Снять все", command=deselect_all).pack(side=tk.LEFT, padx=5)
        
        # Результат
        result = {'apply': False, 'pages': []}
        
        def apply_changes():
            selected_pages = [page_num for page_num, var in page_vars.items() 
                            if var.get() and page_num != self.current_page]
            
            if not selected_pages:
                messagebox.showwarning("Предупреждение", "Выберите хотя бы одну страницу")
                return
            
            # Проверяем, что выбран хотя бы один тип изменений
            apply_del = apply_deletions_var.get() if has_deletions else False
            apply_col = apply_colors_var.get() if has_color_changes else False
            apply_col_rep = apply_color_replacements_var.get() if has_color_replacements else False
            apply_insert = apply_inserted_content_var.get() if has_inserted_content else False
            
            if not apply_del and not apply_col and not apply_col_rep and not apply_insert:
                messagebox.showwarning("Предупреждение", "Выберите хотя бы один тип изменений для применения")
                return
            
            # Применяем изменения
            applied_types = []
            for page_num in selected_pages:
                # Копируем области удаления
                if apply_del and has_deletions:
                    if page_num < len(self.deletion_areas):
                        # Добавляем к существующим (не заменяем)
                        self.deletion_areas[page_num].extend(
                            self.deletion_areas[self.current_page].copy()
                        )
                    else:
                        # Если страница еще не инициализирована
                        while len(self.deletion_areas) <= page_num:
                            self.deletion_areas.append([])
                        self.deletion_areas[page_num] = self.deletion_areas[self.current_page].copy()
                    if "удаления" not in applied_types:
                        applied_types.append("удаления")
                
                # Копируем замены цвета (области)
                if apply_col and has_color_changes:
                    if page_num < len(self.color_changes):
                        # Добавляем к существующим (не заменяем)
                        self.color_changes[page_num].extend(
                            self.color_changes[self.current_page].copy()
                        )
                    else:
                        # Если страница еще не инициализирована
                        while len(self.color_changes) <= page_num:
                            self.color_changes.append([])
                        self.color_changes[page_num] = self.color_changes[self.current_page].copy()
                    if "замены цвета (области)" not in applied_types:
                        applied_types.append("замены цвета (области)")
                
                # Копируем замены цвета на всю страницу (пипетка)
                if apply_col_rep and has_color_replacements:
                    if page_num < len(self.color_replacements):
                        # Добавляем к существующим (не заменяем)
                        self.color_replacements[page_num].extend(
                            self.color_replacements[self.current_page].copy()
                        )
                    else:
                        # Если страница еще не инициализирована
                        while len(self.color_replacements) <= page_num:
                            self.color_replacements.append([])
                        self.color_replacements[page_num] = self.color_replacements[self.current_page].copy()
                    if "замены цвета (вся страница)" not in applied_types:
                        applied_types.append("замены цвета (вся страница)")
                
                # Копируем вставленный контент
                if apply_insert and has_inserted_content:
                    current_page_content = [c.copy() for c in self.inserted_content if c['page'] == self.current_page]
                    for content in current_page_content:
                        content['page'] = page_num
                        self.inserted_content.append(content)
                    if current_page_content and "вставленный контент" not in applied_types:
                        applied_types.append("вставленный контент")
                
                # Инвалидируем кэш для этой страницы
                self.invalidate_preview_cache(page_num)
            
            result['apply'] = True
            result['pages'] = selected_pages
            dialog.destroy()
            
            # Обновляем отображение, если мы на одной из измененных страниц
            if self.current_page in selected_pages:
                self.update_page_display()
            
            types_text = " и ".join(applied_types)
            messagebox.showinfo("Успех", 
                              f"{types_text.capitalize()} применены на {len(selected_pages)} страницах:\n" +
                              ", ".join([f"стр. {p+1}" for p in selected_pages]))
        
        def cancel():
            dialog.destroy()
        
        # Кнопки OK и Отмена
        buttons_frame2 = ttk.Frame(dialog)
        buttons_frame2.pack(padx=10, pady=10)
        
        ttk.Button(buttons_frame2, text="Применить", command=apply_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame2, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=5)
        
        # Ожидание закрытия диалога
        dialog.wait_window()
    
    def apply_colors_to_all_pages(self):
        """Применение замен цвета ко всем страницам"""
        if self.pdf_document is None or self.total_pages == 0:
            messagebox.showwarning("Предупреждение", "Сначала загрузите PDF файл")
            return
        
        # Проверяем, есть ли замены цвета на текущей странице
        has_color_changes = (self.current_page < len(self.color_changes) and 
                           len(self.color_changes[self.current_page]) > 0)
        has_color_replacements = (self.current_page < len(self.color_replacements) and 
                                 len(self.color_replacements[self.current_page]) > 0)
        
        if not has_color_changes and not has_color_replacements:
            messagebox.showinfo("Информация", "На текущей странице нет замен цвета для применения")
            return
        
        # Подтверждение
        result = messagebox.askyesno(
            "Подтверждение",
            f"Применить замены цвета с текущей страницы ({self.current_page + 1}) ко всем {self.total_pages} страницам?\n\n"
            f"Замены цвета (области): {len(self.color_changes[self.current_page]) if has_color_changes else 0}\n"
            f"Замены цвета (вся страница): {len(self.color_replacements[self.current_page]) if has_color_replacements else 0}",
            icon='question'
        )
        
        if not result:
            return
        
        # Применяем изменения ко всем страницам
        applied_count = 0
        for page_num in range(self.total_pages):
            if page_num == self.current_page:
                continue  # Пропускаем текущую страницу
            
            # Применяем замены цвета (области)
            if has_color_changes:
                if page_num < len(self.color_changes):
                    self.color_changes[page_num].extend(
                        self.color_changes[self.current_page].copy()
                    )
                else:
                    while len(self.color_changes) <= page_num:
                        self.color_changes.append([])
                    self.color_changes[page_num] = self.color_changes[self.current_page].copy()
            
            # Применяем замены цвета на всю страницу
            if has_color_replacements:
                if page_num < len(self.color_replacements):
                    self.color_replacements[page_num].extend(
                        self.color_replacements[self.current_page].copy()
                    )
                else:
                    while len(self.color_replacements) <= page_num:
                        self.color_replacements.append([])
                    self.color_replacements[page_num] = self.color_replacements[self.current_page].copy()
            
            # Инвалидируем кэш для этой страницы
            self.invalidate_preview_cache(page_num)
            applied_count += 1
        
        # Обновляем отображение
        self.update_page_display()
        
        messagebox.showinfo("Успех", 
                          f"Замены цвета применены на {applied_count} страницах")
    
    def save_template(self):
        """Сохранение текущих выделений как шаблон"""
        if self.pdf_document is None:
            messagebox.showwarning("Предупреждение", "Сначала загрузите PDF файл")
            return
        
        # Проверяем, есть ли что сохранять
        has_changes = False
        for page_num in range(len(self.deletion_areas)):
            if (page_num < len(self.deletion_areas) and self.deletion_areas[page_num]) or \
               (page_num < len(self.color_changes) and self.color_changes[page_num]) or \
               (page_num < len(self.color_replacements) and self.color_replacements[page_num]):
                has_changes = True
                break
        
        if not has_changes and not self.inserted_content:
            messagebox.showinfo("Информация", "Нет выделений для сохранения в шаблон")
            return
        
        # Диалог сохранения
        template_path = filedialog.asksaveasfilename(
            title="Сохранить шаблон",
            defaultextension=".json",
            filetypes=[("JSON шаблоны", "*.json"), ("All files", "*.*")]
        )
        
        if template_path:
            try:
                # Подготовка данных шаблона
                template_data = {
                    'version': '1.0',
                    'total_pages': len(self.deletion_areas),
                    'deletion_areas': self.deletion_areas,
                    'color_changes': self.color_changes,
                    'color_replacements': self.color_replacements,
                    'inserted_content': self.inserted_content,
                    'target_color': self.target_color
                }
                
                # Сохранение в JSON
                with open(template_path, 'w', encoding='utf-8') as f:
                    json.dump(template_data, f, indent=2, ensure_ascii=False)
                
                self.status_label.config(text=f"Шаблон сохранен: {Path(template_path).name}")
                messagebox.showinfo("Успех", f"Шаблон успешно сохранен:\n{template_path}")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить шаблон: {str(e)}")
    
    def load_template(self):
        """Загрузка шаблона выделений"""
        if self.pdf_document is None:
            messagebox.showwarning("Предупреждение", "Сначала загрузите PDF файл")
            return
        
        # Диалог загрузки
        template_path = filedialog.askopenfilename(
            title="Загрузить шаблон",
            filetypes=[("JSON шаблоны", "*.json"), ("All files", "*.*")]
        )
        
        if template_path:
            try:
                # Загрузка из JSON
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                # Проверка версии и структуры
                if 'version' not in template_data:
                    messagebox.showerror("Ошибка", "Неверный формат шаблона")
                    return
                
                template_pages = template_data.get('total_pages', 0)
                current_pages = self.total_pages
                
                # Проверяем, есть ли существующие выделения
                has_existing = False
                for page_num in range(current_pages):
                    if (page_num < len(self.deletion_areas) and self.deletion_areas[page_num]) or \
                       (page_num < len(self.color_changes) and self.color_changes[page_num]) or \
                       (page_num < len(self.color_replacements) and self.color_replacements[page_num]):
                        has_existing = True
                        break
                
                # Диалог выбора способа применения
                replace_mode = False
                if template_pages != current_pages:
                    result = messagebox.askyesno(
                        "Несоответствие страниц",
                        f"Шаблон содержит {template_pages} страниц, а текущий PDF - {current_pages}.\n\n"
                        "Применить шаблон к текущему PDF?\n"
                        "(Будут применены только данные для существующих страниц)",
                        icon='question'
                    )
                    if not result:
                        return
                elif has_existing:
                    # Спрашиваем, заменять или добавлять
                    dialog = tk.Toplevel(self.root)
                    dialog.title("Способ применения шаблона")
                    dialog.geometry("400x150")
                    dialog.transient(self.root)
                    dialog.grab_set()
                    
                    # Центрируем окно
                    dialog.update_idletasks()
                    x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
                    y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
                    dialog.geometry(f"+{x}+{y}")
                    
                    ttk.Label(dialog, text="На текущем PDF уже есть выделения.\nВыберите способ применения шаблона:", 
                             font=("Arial", 9)).pack(padx=10, pady=10)
                    
                    mode_var = tk.StringVar(value="add")
                    
                    ttk.Radiobutton(dialog, text="Добавить к существующим выделениям", 
                                   variable=mode_var, value="add").pack(anchor=tk.W, padx=20, pady=5)
                    ttk.Radiobutton(dialog, text="Заменить существующие выделения", 
                                   variable=mode_var, value="replace").pack(anchor=tk.W, padx=20, pady=5)
                    
                    result_var = {'confirmed': False}
                    
                    def confirm():
                        result_var['confirmed'] = True
                        result_var['mode'] = mode_var.get()
                        dialog.destroy()
                    
                    def cancel():
                        dialog.destroy()
                    
                    buttons_frame = ttk.Frame(dialog)
                    buttons_frame.pack(padx=10, pady=10)
                    ttk.Button(buttons_frame, text="Применить", command=confirm).pack(side=tk.LEFT, padx=5)
                    ttk.Button(buttons_frame, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=5)
                    
                    dialog.wait_window()
                    
                    if not result_var.get('confirmed'):
                        return
                    
                    replace_mode = (result_var.get('mode') == 'replace')
                
                # Применение шаблона
                applied_pages = 0
                
                # Применяем удаления
                if 'deletion_areas' in template_data:
                    for page_num in range(min(template_pages, current_pages)):
                        if page_num < len(template_data['deletion_areas']):
                            if page_num < len(self.deletion_areas):
                                if replace_mode:
                                    self.deletion_areas[page_num] = template_data['deletion_areas'][page_num].copy()
                                else:
                                    self.deletion_areas[page_num].extend(template_data['deletion_areas'][page_num].copy())
                            else:
                                while len(self.deletion_areas) <= page_num:
                                    self.deletion_areas.append([])
                                self.deletion_areas[page_num] = template_data['deletion_areas'][page_num].copy()
                            if template_data['deletion_areas'][page_num]:
                                applied_pages = max(applied_pages, page_num + 1)
                
                # Применяем замены цвета (области)
                if 'color_changes' in template_data:
                    for page_num in range(min(template_pages, current_pages)):
                        if page_num < len(template_data['color_changes']):
                            if page_num < len(self.color_changes):
                                if replace_mode:
                                    self.color_changes[page_num] = template_data['color_changes'][page_num].copy()
                                else:
                                    self.color_changes[page_num].extend(template_data['color_changes'][page_num].copy())
                            else:
                                while len(self.color_changes) <= page_num:
                                    self.color_changes.append([])
                                self.color_changes[page_num] = template_data['color_changes'][page_num].copy()
                            if template_data['color_changes'][page_num]:
                                applied_pages = max(applied_pages, page_num + 1)
                
                # Применяем замены цвета (вся страница)
                if 'color_replacements' in template_data:
                    for page_num in range(min(template_pages, current_pages)):
                        if page_num < len(template_data['color_replacements']):
                            if page_num < len(self.color_replacements):
                                if replace_mode:
                                    self.color_replacements[page_num] = template_data['color_replacements'][page_num].copy()
                                else:
                                    self.color_replacements[page_num].extend(template_data['color_replacements'][page_num].copy())
                            else:
                                while len(self.color_replacements) <= page_num:
                                    self.color_replacements.append([])
                                self.color_replacements[page_num] = template_data['color_replacements'][page_num].copy()
                            if template_data['color_replacements'][page_num]:
                                applied_pages = max(applied_pages, page_num + 1)
                
                # Применяем вставленный контент
                if 'inserted_content' in template_data:
                    if replace_mode:
                        # Заменяем существующий контент
                        self.inserted_content = template_data['inserted_content'].copy()
                    else:
                        # Добавляем к существующему контенту
                        self.inserted_content.extend(template_data['inserted_content'].copy())
                    
                    # Фильтруем контент для существующих страниц
                    self.inserted_content = [c for c in self.inserted_content if c['page'] < current_pages]
                    if self.inserted_content:
                        applied_pages = max(applied_pages, max(c['page'] for c in self.inserted_content) + 1)
                
                # Применяем целевой цвет, если есть
                if 'target_color' in template_data:
                    self.target_color = template_data['target_color']
                    self.color_btn.config(bg=self.target_color)
                
                # Инвалидируем кэш для всех страниц
                for page_num in range(current_pages):
                    self.invalidate_preview_cache(page_num)
                
                # Обновляем отображение
                self.update_page_display()
                self.update_info_panels()
                
                self.status_label.config(text=f"Шаблон загружен: {Path(template_path).name}")
                messagebox.showinfo("Успех", 
                                  f"Шаблон успешно загружен и применен к {applied_pages} страницам")
                
            except json.JSONDecodeError:
                messagebox.showerror("Ошибка", "Неверный формат JSON файла")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить шаблон: {str(e)}")
    
    def update_info_panels(self):
        """Обновление информационных панелей"""
        # Очистка списков
        self.deletion_listbox.delete(0, tk.END)
        self.color_listbox.delete(0, tk.END)
        
        if (self.pdf_document is None or 
            not (0 <= self.current_page < len(self.deletion_areas))):
            return
        
        # Заполнение списков для текущей страницы
        for area in self.deletion_areas[self.current_page]:
            x1, y1, x2, y2 = area
            self.deletion_listbox.insert(
                tk.END, 
                f"({int(x1)},{int(y1)})-({int(x2)},{int(y2)})"
            )
        
        if self.current_page < len(self.color_changes):
            for change in self.color_changes[self.current_page]:
                area, orig_color, new_color = change
                self.color_listbox.insert(tk.END, f"{orig_color} → {new_color}")
        
        # Отображение замен цвета на всю страницу (пипетка)
        if self.current_page < len(self.color_replacements):
            for replacement in self.color_replacements[self.current_page]:
                old_color = replacement['old_color']
                new_color = replacement['new_color']
                self.color_listbox.insert(tk.END, f"Вся страница: {old_color} → {new_color}")
        
        # Отображение вставленного контента
        for content in self.inserted_content:
            if content['page'] == self.current_page:
                if content['type'] == 'text':
                    text_preview = content['data']['text'][:30] + "..." if len(content['data']['text']) > 30 else content['data']['text']
                    self.color_listbox.insert(tk.END, f"Текст: {text_preview} @ ({int(content['x'])}, {int(content['y'])})")
                elif content['type'] == 'image':
                    img_name = Path(content['data']['path']).name
                    self.color_listbox.insert(tk.END, f"Изображение: {img_name} @ ({int(content['x'])}, {int(content['y'])})")
    
    def prev_page(self):
        """Переход к предыдущей странице"""
        if self.pdf_document and self.current_page > 0:
            self.current_page -= 1
            self.update_page_display()
    
    def next_page(self):
        """Переход к следующей странице"""
        if self.pdf_document and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_display()
    
    def zoom_in(self):
        """Увеличение масштаба"""
        if self.pdf_document:
            new_zoom = self.zoom * 1.2
            if new_zoom <= 5.0:  # Ограничение максимального масштаба
                self.zoom = new_zoom
                self.page_images[self.current_page] = None
                self.invalidate_preview_cache(self.current_page)
                self.update_page_display()
    
    def zoom_out(self):
        """Уменьшение масштаба"""
        if self.pdf_document:
            new_zoom = self.zoom / 1.2
            if new_zoom >= 0.2:  # Ограничение минимального масштаба
                self.zoom = new_zoom
                self.page_images[self.current_page] = None
                self.invalidate_preview_cache(self.current_page)
                self.update_page_display()
    
    def reset_zoom(self):
        """Сброс масштаба"""
        if self.pdf_document:
            self.zoom = 1.0
            self.page_images[self.current_page] = None
            self.invalidate_preview_cache(self.current_page)
            self.update_page_display()
    
    def apply_changes_to_page(self, page_num):
        """Применение изменений к странице PDF"""
        if (not self.pdf_document or page_num < 0 or 
            page_num >= self.total_pages or 
            page_num >= len(self.deletion_areas)):
            return None
            
        try:
            page = self.pdf_document[page_num]
            page_rect = page.rect
            
            # Создание нового документа для этой страницы
            doc = fitz.open()
            new_page = doc.new_page(width=page_rect.width, height=page_rect.height)
            
            # Проверяем, есть ли замены цвета на всю страницу или вставленный контент
            has_full_page_color_replacements = (page_num < len(self.color_replacements) and 
                                               self.color_replacements[page_num])
            has_inserted_content = any(c['page'] == page_num for c in self.inserted_content)
            
            if has_full_page_color_replacements or has_inserted_content:
                # Если есть замены цвета на всю страницу, используем изображение
                # Получаем изображение страницы
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Применяем все изменения к изображению
                img_with_changes = self.apply_changes_to_image(img, page_num, 1.0)
                
                # Конвертируем обратно в pixmap и вставляем в PDF
                img_bytes = io.BytesIO()
                img_with_changes.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                
                # Вставляем изображение на страницу
                img_rect = fitz.Rect(0, 0, page_rect.width, page_rect.height)
                new_page.insert_image(img_rect, stream=img_bytes.getvalue())
            else:
                # Вставка оригинальной страницы
                new_page.show_pdf_page(new_page.rect, self.pdf_document, page_num)
                
                # Применение удалений (закрашивание белым)
                for area in self.deletion_areas[page_num]:
                    x1, y1, x2, y2 = area
                    # Валидация координат
                    x1 = max(0, min(x1, page_rect.width))
                    y1 = max(0, min(y1, page_rect.height))
                    x2 = max(0, min(x2, page_rect.width))
                    y2 = max(0, min(y2, page_rect.height))
                    
                    if x1 < x2 and y1 < y2:
                        rect = fitz.Rect(x1, y1, x2, y2)
                        new_page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                
                # Применение замены цвета в выделенных областях
                if page_num < len(self.color_changes):
                    for area, orig_color, new_color in self.color_changes[page_num]:
                        x1, y1, x2, y2 = area
                        # Валидация координат
                        x1 = max(0, min(x1, page_rect.width))
                        y1 = max(0, min(y1, page_rect.height))
                        x2 = max(0, min(x2, page_rect.width))
                        y2 = max(0, min(y2, page_rect.height))
                        
                        if x1 < x2 and y1 < y2:
                            rect = fitz.Rect(x1, y1, x2, y2)
                            
                            # Конвертация hex цвета в RGB
                            if new_color and new_color.startswith('#'):
                                try:
                                    r = int(new_color[1:3], 16) / 255.0
                                    g = int(new_color[3:5], 16) / 255.0
                                    b = int(new_color[5:7], 16) / 255.0
                                    new_page.draw_rect(rect, color=(r, g, b), fill=(r, g, b))
                                except (ValueError, IndexError):
                                    # Если цвет некорректный, пропускаем
                                    pass
                
                # Применение вставленного контента (только если нет замен цвета на всю страницу)
                if not has_full_page_color_replacements:
                    for content in self.inserted_content:
                        if content['page'] == page_num:
                            try:
                                if content['type'] == 'text':
                                    # Вставляем текст
                                    text = content['data']['text']
                                    font_size = content['data']['font_size']
                                    color_hex = content['data']['color']
                                    
                                    # Конвертируем цвет
                                    r = int(color_hex[1:3], 16) / 255.0
                                    g = int(color_hex[3:5], 16) / 255.0
                                    b = int(color_hex[5:7], 16) / 255.0
                                    
                                    # Вставляем текст
                                    point = fitz.Point(content['x'], content['y'])
                                    new_page.insert_text(
                                        point,
                                        text,
                                        fontsize=font_size,
                                        color=(r, g, b)
                                    )
                                
                                elif content['type'] == 'image':
                                    # Вставляем изображение
                                    img_path = content['data']['path']
                                    if Path(img_path).exists():
                                        width = content['data']['width']
                                        height = content['data']['height']
                                        
                                        # Открываем изображение
                                        img = Image.open(img_path)
                                        
                                        # Изменяем размер, если нужно
                                        if width > 0 or height > 0:
                                            if width > 0 and height > 0:
                                                img = img.resize((width, height), Image.Resampling.LANCZOS)
                                            elif width > 0:
                                                ratio = width / img.width
                                                img = img.resize((width, int(img.height * ratio)), Image.Resampling.LANCZOS)
                                            elif height > 0:
                                                ratio = height / img.height
                                                img = img.resize((int(img.width * ratio), height), Image.Resampling.LANCZOS)
                                        
                                        # Конвертируем в bytes
                                        img_bytes = io.BytesIO()
                                        img.save(img_bytes, format='PNG')
                                        img_bytes.seek(0)
                                        
                                        # Вставляем изображение
                                        rect = fitz.Rect(
                                            content['x'],
                                            content['y'],
                                            content['x'] + img.width,
                                            content['y'] + img.height
                                        )
                                        new_page.insert_image(rect, stream=img_bytes.getvalue())
                            except Exception as e:
                                # Если не удалось вставить контент, пропускаем
                                pass
            
            return doc
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось применить изменения к странице {page_num + 1}: {str(e)}")
            return None
    
    def save_pdf(self):
        """Сохранение отредактированного PDF"""
        if self.pdf_document is None:
            messagebox.showwarning("Предупреждение", "Сначала загрузите PDF файл")
            return
            
        save_path = filedialog.asksaveasfilename(
            title="Сохранить PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if save_path:
            new_doc = None
            try:
                # Создание нового PDF документа
                new_doc = fitz.open()
                
                # Обработка каждой страницы
                for page_num in range(self.total_pages):
                    temp_doc = None
                    try:
                        has_changes = (
                            (page_num < len(self.deletion_areas) and len(self.deletion_areas[page_num]) > 0) or
                            (page_num < len(self.color_changes) and len(self.color_changes[page_num]) > 0) or
                            (page_num < len(self.color_replacements) and len(self.color_replacements[page_num]) > 0)
                        )
                        
                        if not has_changes:
                            # Если нет изменений, копируем оригинальную страницу
                            new_doc.insert_pdf(self.pdf_document, from_page=page_num, to_page=page_num)
                        else:
                            # Применяем изменения к странице
                            temp_doc = self.apply_changes_to_page(page_num)
                            if temp_doc:
                                new_doc.insert_pdf(temp_doc)
                    finally:
                        if temp_doc is not None:
                            temp_doc.close()
                
                # Сохранение нового документа
                new_doc.save(save_path)
                self.status_label.config(text=f"Сохранено: {Path(save_path).name}")
                messagebox.showinfo("Успех", f"PDF успешно сохранен как:\n{save_path}")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить PDF: {str(e)}")
            finally:
                if new_doc is not None:
                    new_doc.close()


def main():
    root = tk.Tk()
    app = PDFEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()