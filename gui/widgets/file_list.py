import tkinter as tk
from tkinter import ttk


class FileListWidget(ttk.Frame):
    """Виджет для отображения списка файлов"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.double_click_callback = None
        self.folder_change_callback = None

        self.create_widgets()

    def create_widgets(self):
        """Создаёт элементы интерфейса"""
        # Заголовок
        title = ttk.Label(
            self,
            text="Файлы и папки",
            font=('Arial', 10, 'bold')
            )
        title.pack(pady=5)

        # Создаём treeview с колонками
        columns = ('name', 'type', 'size', 'modified', 'tags')
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show='headings',
            height=20
            )

        # Настройка колонок
        self.tree.heading('name', text='Имя')
        self.tree.heading('type', text='Тип')
        self.tree.heading('size', text='Размер')
        self.tree.heading('modified', text='Изменён')
        self.tree.heading('tags', text='Теги')

        self.tree.column('name', width=300)
        self.tree.column('type', width=80)
        self.tree.column('size', width=100)
        self.tree.column('modified', width=150)
        self.tree.column('tags', width=150)

        # Скроллбар
        scrollbar = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL,
            command=self.tree.yview
            )
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Размещение
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Привязываем события
        self.tree.bind('<Double-1>', self.on_double_click)

    def update_files(self, files):
        """обновляет список файлов"""
        # Очищаем текущий список
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Добавляем новые файлы
        for f in files:
            item_type = 'Папка' if f.type == 'dir' else 'Файл'
            size = self._format_size(getattr(f, 'size', 0))
            modified = f.modified.strftime('%d.%m.%Y %H:%M')if hasattr(
                f, 'modified') else ''

            # Сохраняем полный путь и другие данные в tags
            values = (
                f.name,
                item_type,
                size,
                modified,
                ''  # теги пока пустые
            )

            item_id = self.tree.insert('', tk.END, values=values)

            # Сохраняем дополнительные данные в item
            self.tree.set(item_id, 'name', f.name)

            # Храним информацию о файле в отдельном словаре
            if not hasattr(self, '_items_data'):
                self._items_data = {}
            self._items_data[item_id] = {
                'name': f.name,
                'path': f.path,
                'type': f.type,
                'size': getattr(f, 'size', 0),
                'modified': modified,
                'resource_id': getattr(f, 'resource_id', None)
            }

    def _format_size(self, size):
        """Форматирует размер файла"""
        if size is None or size == 0:
            return ''
        elif size < 1024:
            return f"{size} Б"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} КБ"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} МБ"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} ГБ"

    def on_double_click(self, event):
        """Обработка двойного клика"""
        selection = self.tree.seelction()
        if not selection:
            return

        item_id = selection[0]
        if hasattr(self, '_items_data') and item_id in self._items_data:
            item = self._items_data[item_id]
            if self.double_click_callback:
                self.double_click_callback(item)

    def bind_double_click(self, callback):
        """Привязывает обработчик двойного клика"""
        self.double_click_callback = callback

    def bind_folder_change(self, callback):
        """Привязывает обработчик смены папки"""
        self.folder_change_callback = callback

    def get_selected_item(self):
        """Возвращает выбранный элемент"""
        selection = self.tree.selection()
        if not selection:
            return None

        item_id = selection[0]
        if hasattr(self, '_items_data') and item_id in self._items_data:
            return self._items_data[item_id]
        return None
