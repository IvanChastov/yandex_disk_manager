import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Tag


class TagAssignDialog:
    """Диалог для назначения тегов файлу"""
    
    def __init__(self, parent, file_path, current_tags):
        self.parent = parent
        self.file_path = file_path
        self.current_tags = set(current_tags)
        self.result = None
        
        # Создаём окно
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Назначить теги")
        self.dialog.geometry("450x550")
        self.dialog.minsize(400, 500)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Создаём все элементы
        self.create_widgets()
        
        # Центрируем
        self.center_window()
    
    def create_widgets(self):
        # Основной фрейм
        main = ttk.Frame(self.dialog, padding="15")
        main.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        ttk.Label(main, text="Выберите теги для файла:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        
        # Имя файла
        file_name = self.file_path.split('/')[-1]
        ttk.Label(main, text=file_name, foreground="blue").pack(anchor=tk.W, pady=5)
        
        # Кнопка создания тега
        ttk.Button(main, text="+ Создать новый тег", command=self.add_tag).pack(anchor=tk.W, pady=10)
        
        # Рамка для списка
        frame = ttk.LabelFrame(main, text="Доступные теги", padding=5)
        frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Список
        self.listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=12, font=('Arial', 10))
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Загружаем теги
        self.load_tags()
        
        # Кнопки
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Сохранить", command=self.on_ok, width=12).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=self.on_cancel, width=12).pack(side=tk.RIGHT)
    
    def center_window(self):
        self.dialog.update_idletasks()
        w = self.dialog.winfo_width()
        h = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f'{w}x{h}+{x}+{y}')
    
    def load_tags(self):
        self.listbox.delete(0, tk.END)
        self.tag_names = []
        
        for tag in Tag.objects.all().order_by('name'):
            self.tag_names.append(tag.name)
            self.listbox.insert(tk.END, tag.name)
            if tag.name in self.current_tags:
                self.listbox.selection_set(tk.END)
    
    def add_tag(self):
        name = simpledialog.askstring("Новый тег", "Введите название тега:", parent=self.dialog)
        if name:
            if Tag.objects.filter(name=name).exists():
                messagebox.showwarning("Ошибка", "Тег уже существует")
            else:
                Tag.objects.create(name=name)
                self.load_tags()
    
    def on_ok(self):
        indices = self.listbox.curselection()
        self.result = [self.tag_names[i] for i in indices]
        self.dialog.destroy()
    
    def on_cancel(self):
        self.dialog.destroy()
    
    def run(self):
        self.dialog.wait_window()
        return self.result
