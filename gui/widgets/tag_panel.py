import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
    )

# Настраиваем django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Tag


class TagPanel(ttk.Frame):
    """Виджет для отображения и управления тегами"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.create_widgets()
        self.load_tags()

    def create_widgets(self):
        """Создаёт элементы интерфейса"""
        # Заголовок
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, pady=5)

        ttk.Label(title_frame, text="Теги", font=('Arial', 10, 'bold')).pack(
            side=tk.LEFT
            )

        # Кнопка добавления тега
        add_button = ttk.Button(
            title_frame,
            text="+",
            width=3,
            command=self.add_tag
        )
        add_button.pack(side=tk.RIGHT)

        # Список тегов
        self.tag_listbox = tk.Listbox(self, height=15)
        self.tag_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        # Привязываем события
        self.tag_listbox.bind('<Double-1>', self.on_tag_double_click)
        self.tag_listbox.bind('<Delete>', self.on_tag_delete)

        # Поиск по тегам
        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, pady=5)

        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT)
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind('<KeyRelease>', self.on_search)

    def load_tags(self):
        """Загружает теги из БД"""
        self.tag_listbox.delete(0, tk.END)

        tags = Tag.objects.all().order_by('name')
        for tag in tags:
            self.tag_listbox.insert(tk.END, tag.name)

    def add_tag(self):
        """Добавляет новый тег"""
        name = simpledialog.askstring(
            "Добавить тег",
            "Введите название тега:",
            parent=self
        )

        if not name:
            return

        # Проверяем, существует ли тег
        if Tag.objects.filter(name=name).exists():
            messagebox.showwarning(
                "Предупреждение", f"Тег '{name}' уже существует"
                )
            return

        # Создаём тег
        try:
            # Пока создаём без created_by
            tag = Tag.objects.create(name=name)
            self.load_tags()
            messagebox.showinfo("Успех", f"Тег '{name}' создан")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать тег: {e}")

    def delete_tag(self, tag_name):
        """Удаляет тег"""
        try:
            tag = Tag.objects.get(name=tag_name)
            tag.delete()
            self.load_tags()
        except Tag.DoesNotExist:
            pass

    def on_tag_double_click(self, event):
        """Обработка двойного клика по тегу"""
        selection = self.tag_listbox.curselection()
        if selection:
            tag_name = self.tag_listbox.get(selection[0])
            # TODO: фильтрация файлов по тегу
            print(f"Выбран тег: {tag_name}")

    def on_tag_delete(self, event):
        """Обработка удаления тега (клавиша Delete)"""
        selection = self.tag_listbox.curselection()
        if selection:
            tag_name = self.tag_listbox.get(selection[0])
            if messagebox.askyesno(
                "удалить тег", f"Удалить тег '{tag_name}'?"
            ):
                self.delete_tag(tag_name)

    def on_search(self, event):
        """Поиск тегов"""
        query = self.search_entry.get().lower()

        self.tag_listbox.delete(0, tk.END)

        tags = Tag.objects.filter(name___icontains=query).order_by('name')
        for tag in tags:
            self.tag_listbox.insert(tk.END, tag.name)

    def get_selected_tag(self):
        """Возвращает выбранный тег"""
        selection = self.tag_listbox.curselection()
        if selection:
            return self.tag_listbox.get(selection[0])
        return None
