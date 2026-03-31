import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from PIL import Image, ImageTk

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.yandex.client import YandexDiskClient
from core.yandex.storage import get_current_user


class PreviewDialog:
    """Диалог предпросмотра файла"""
    
    # Расширения, поддерживаемые для предпросмотра
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    TEXT_EXTENSIONS = {'.txt', '.py', '.json', '.xml', '.html', '.css', '.js', '.md', '.log', 'docx'}
    CAD_EXTENSIONS = {'.dwg', '.dxf'}
    PDF_EXTENSIONS = {'.pdf'}
    
    def __init__(self, parent, file_item):
        self.parent = parent
        self.file_item = file_item
        self.client = None
        self.temp_file = None
        
        self.file_name = file_item.get('name')
        self.file_path = file_item.get('path')
        self.file_ext = os.path.splitext(self.file_name)[1].lower()
        
        # Создаём клиент
        username = get_current_user()
        if username:
            try:
                self.client = YandexDiskClient(username=username)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать клиент: {e}")
                return
        
        # Создаём окно
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Предпросмотр: {self.file_name}")
        self.dialog.geometry("800x600")
        self.dialog.minsize(600, 500)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        self.load_preview()
        self.center_window()
    
    def center_window(self):
        self.dialog.update_idletasks()
        w = self.dialog.winfo_width()
        h = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f'{w}x{h}+{x}+{y}')
    
    def create_widgets(self):
        # Основной фрейм
        main = ttk.Frame(self.dialog, padding="10")
        main.pack(fill=tk.BOTH, expand=True)
        
        # Информация о файле
        info_frame = ttk.Frame(main)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(info_frame, text="Файл:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        ttk.Label(info_frame, text=self.file_name).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(info_frame, text="Тип:", font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=(20, 0))
        ttk.Label(info_frame, text=self.file_ext.upper() if self.file_ext else "Неизвестно").pack(side=tk.LEFT, padx=5)
        
        # Область предпросмотра
        self.preview_frame = ttk.Frame(main, relief=tk.SUNKEN, borderwidth=1)
        self.preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # Метка для отображения содержимого
        self.preview_label = ttk.Label(self.preview_frame, text="Загрузка...")
        self.preview_label.pack(expand=True)
        
        # Кнопки
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(
            btn_frame,
            text="Открыть в программе",
            command=self.open_external
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Закрыть",
            command=self.on_close
        ).pack(side=tk.RIGHT, padx=5)
    
    def load_preview(self):
        """Загружает и отображает предпросмотр файла"""
        if not self.client:
            self.preview_label.config(text="Ошибка: не удалось создать клиент")
            return
        
        import tempfile
        
        try:
            # Создаём временный файл
            temp_dir = tempfile.gettempdir()
            self.temp_file = os.path.join(temp_dir, f"preview_{os.urandom(8).hex()}_{self.file_name}")
            
            # Скачиваем
            success = self.client.download_file(self.file_path, self.temp_file)
            
            if not success:
                self.preview_label.config(text="Ошибка: не удалось скачать файл")
                return
            
            # Отображаем в зависимости от типа
            if self.file_ext in self.IMAGE_EXTENSIONS:
                self.show_image_preview()
            elif self.file_ext in self.TEXT_EXTENSIONS:
                self.show_text_preview()
            elif self.file_ext in self.CAD_EXTENSIONS:
                self.show_cad_preview()
            elif self.file_ext in self.PDF_EXTENSIONS:
                self.show_pdf_preview()
            else:
                self.preview_label.config(
                    text=f"Предпросмотр для файлов типа {self.file_ext} не поддерживается.\n"
                         f"Нажмите 'Открыть в программе' для просмотра."
                )
                
        except Exception as e:
            self.preview_label.config(text=f"Ошибка загрузки: {e}")
    
    def show_image_preview(self):
        """Отображает предпросмотр изображения"""
        try:
            # Открываем изображение
            image = Image.open(self.temp_file)
            
            # Получаем размеры окна
            frame_width = self.preview_frame.winfo_width()
            frame_height = self.preview_frame.winfo_height()
            
            if frame_width <= 1:
                frame_width = 700
                frame_height = 550
            
            # Масштабируем изображение
            img_width, img_height = image.size
            scale = min(frame_width / img_width, frame_height / img_height, 1.0)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Если изображение большое, увеличиваем окно
            if img_width > 800 or img_height > 600:
                # Увеличиваем окно до разумных пределов
                new_win_width = min(img_width + 50, 1200)
                new_win_height = min(img_height + 100, 900)
                self.dialog.geometry(f"{new_win_width}x{new_win_height}")
                self.dialog.update_idletasks()
            
            if scale < 1:
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Конвертируем для Tkinter
            photo = ImageTk.PhotoImage(image)
            
            # Обновляем отображение
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo
            
            # Добавляем информацию о размере
            size_info = f"{img_width}x{img_height} (отображено: {new_width}x{new_height})"
            ttk.Label(self.preview_frame, text=size_info, foreground="gray").pack(side=tk.BOTTOM)
            
        except Exception as e:
            self.preview_label.config(text=f"Ошибка отображения изображения: {e}")
    
    def show_text_preview(self):
        """Отображает предпросмотр текстового файла"""
        try:
            # Увеличиваем окно для текста
            self.dialog.geometry("900x700")
            self.dialog.update_idletasks()
            
            # Читаем файл
            with open(self.temp_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(10000)
            
            # Создаём текстовое поле с прокруткой
            text_frame = ttk.Frame(self.preview_frame)
            text_frame.pack(fill=tk.BOTH, expand=True)
            
            text_widget = tk.Text(text_frame, wrap=tk.WORD, font=('Courier', 10))
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            text_widget.insert(tk.END, content)
            text_widget.config(state=tk.DISABLED)  # Только для чтения
            
            self.preview_label.destroy()
            
            # Если файл больше 10000 символов
            if len(content) >= 10000:
                info = ttk.Label(self.preview_frame, text="(Показано первые 10000 символов)", foreground="gray")
                info.pack(side=tk.BOTTOM)
                
        except Exception as e:
            self.preview_label.config(text=f"Ошибка чтения текстового файла: {e}")

    def show_cad_preview(self):
        """Отображает информацию о CAD-файле и предлагает открыть в программе"""
        # Очищаем фрейм
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        # Информационная панель
        info_frame = ttk.Frame(self.preview_frame)
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        # Иконка (текстовая)
        icon_label = ttk.Label(
            info_frame,
            text="[CAD]",
            font=('Arial', 48, 'bold'),
            foreground="#2c3e50"
        )
        icon_label.pack(pady=20)
        
        # Информация о формате
        format_name = "AutoCAD DWG" if self.file_ext == '.dwg' else "AutoCAD DXF"
        ttk.Label(
            info_frame,
            text=f"Формат: {format_name}",
            font=('Arial', 12, 'bold')
        ).pack(pady=5)
        
        ttk.Label(
            info_frame,
            text="Для просмотра этого файла требуется специализированное ПО.\n"
                 "Нажмите кнопку ниже, чтобы открыть файл в установленной программе.",
            justify=tk.CENTER
        ).pack(pady=10)
        
        # Кнопки открытия
        btn_frame = ttk.Frame(info_frame)
        btn_frame.pack(pady=10)
        
        # Кнопка открытия в AutoCAD
        ttk.Button(
            btn_frame,
            text="Открыть в AutoCAD",
            command=self.open_cad
        ).pack(side=tk.LEFT, padx=5)
        
        # Кнопка открытия в программе по умолчанию
        ttk.Button(
            btn_frame,
            text="Открыть в программе по умолчанию",
            command=self.open_external
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="Онлайн просмотр (Autodesk Viewer)",
            command=self.open_online_viewer
        ).pack(side=tk.LEFT, padx=5)
        
        # Информация о возможных программах
        programs = [
            "• AutoCAD (Autodesk)",
            "• DWG TrueView (бесплатный просмотрщик Autodesk)",
            "• nanoCAD (российский аналог)",
            "• LibreCAD (бесплатный, открытый код)",
            "• онлайн-просмотрщики (Autodesk Viewer, A360)"
        ]
        
        ttk.Label(
            info_frame,
            text="\nПрограммы для просмотра:\n" + "\n".join(programs),
            justify=tk.LEFT,
            foreground="gray"
        ).pack(pady=10)
    
    def show_pdf_preview(self):
        """Отображает информацию о PDF и предлагает открыть в программе"""
        # Очищаем фрейм
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        # Информационная панель
        info_frame = ttk.Frame(self.preview_frame)
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        # Иконка (текстовая)
        icon_label = ttk.Label(
            info_frame,
            text="[PDF]",
            font=('Arial', 48, 'bold'),
            foreground="#e67e22"
        )
        icon_label.pack(pady=20)
        
        # Информация о формате
        ttk.Label(
            info_frame,
            text="Формат: PDF (Portable Document Format)",
            font=('Arial', 12, 'bold')
        ).pack(pady=5)
        
        # Информация о файле
        file_size = self.file_item.get('size', 0)
        size_str = self._format_size(file_size)
        
        ttk.Label(
            info_frame,
            text=f"Имя: {self.file_name}\nРазмер: {size_str}",
            justify=tk.CENTER
        ).pack(pady=5)
        
        ttk.Label(
            info_frame,
            text="Для просмотра PDF-файла нажмите кнопку ниже.",
            justify=tk.CENTER
        ).pack(pady=10)
        
        # Кнопки
        btn_frame = ttk.Frame(info_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(
            btn_frame,
            text="Открыть PDF",
            command=self.open_external
        ).pack(side=tk.LEFT, padx=5)
        
        # Информация о программах
        programs = [
            "• Adobe Acrobat Reader",
            "• Встроенный просмотрщик браузера",
            "• Foxit Reader",
            "• SumatraPDF (лёгкий просмотрщик)"
        ]
        
        ttk.Label(
            info_frame,
            text="\nПрограммы для просмотра PDF:\n" + "\n".join(programs),
            justify=tk.LEFT,
            foreground="gray"
        ).pack(pady=10)
    
    def _format_size(self, size):
        """Форматирует размер файла"""
        if size is None or size == 0:
            return "неизвестно"
        elif size < 1024:
            return f"{size} Б"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} КБ"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} МБ"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} ГБ"
    
    def open_external(self):
        """Открывает файл в программе по умолчанию"""
        import subprocess
        import platform
        
        if not self.temp_file or not os.path.exists(self.temp_file):
            messagebox.showerror("Ошибка", "Файл не загружен")
            return
        
        try:
            if platform.system() == "Windows":
                os.startfile(self.temp_file)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", self.temp_file])
            else:  # Linux
                subprocess.run(["xdg-open", self.temp_file])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")

    def open_cad(self):
        """Пытается открыть файл в AutoCAD или другой CAD-программе"""
        import subprocess
        import platform
        import os
        
        if not self.temp_file or not os.path.exists(self.temp_file):
            messagebox.showerror("Ошибка", "Файл не загружен")
            return
        
        # Список возможных CAD-программ (по убыванию приоритета)
        cad_programs = []
        
        if platform.system() == "Windows":
            cad_programs = [
                r"C:\Program Files\Autodesk\AutoCAD 2024\acad.exe",
                r"C:\Program Files\Autodesk\AutoCAD 2023\acad.exe",
                r"C:\Program Files\Autodesk\AutoCAD 2022\acad.exe",
                r"C:\Program Files\Autodesk\AutoCAD 2021\acad.exe",
                r"C:\Program Files\Autodesk\AutoCAD LT 2024\acadlt.exe",
                r"C:\Program Files\nanoCAD\nanoCAD 23\bin\nanoCAD.exe",
                r"C:\Program Files (x86)\LibreCAD\librecad.exe"
            ]
        
        # Пробуем найти установленную программу
        found_program = None
        for prog in cad_programs:
            if os.path.exists(prog):
                found_program = prog
                break
        
        if found_program:
            try:
                subprocess.run([found_program, self.temp_file])
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл в CAD:\n{e}")
        else:
            # Если AutoCAD не найден, открываем в программе по умолчанию
            result = messagebox.askyesno(
                "CAD не найден",
                "AutoCAD не обнаружен на этом компьютере.\n"
                "Открыть файл в программе по умолчанию?"
            )
            if result:
                self.open_external()

    def open_online_viewer(self):
        """Открывает файл в онлайн-просмотрщике Autodesk Viewer"""
        import webbrowser
        
        # Autodesk Viewer позволяет загружать файлы для просмотра
        url = "https://viewer.autodesk.com/"
        webbrowser.open(url)
        
        messagebox.showinfo(
            "Онлайн просмотр",
            "Открыт Autodesk Viewer.\n"
            "Загрузите файл в интерфейсе для просмотра.\n\n"
            f"Файл временно сохранён в:\n{self.temp_file}"
        )
    
    def on_close(self):
        """Закрывает диалог и удаляет временный файл"""
        if self.temp_file and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except:
                pass
        self.dialog.destroy()
    
    def run(self):
        self.dialog.wait_window()
