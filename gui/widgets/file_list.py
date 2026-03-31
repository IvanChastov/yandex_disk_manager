import tkinter as tk
from tkinter import ttk


class FileListWidget(ttk.Frame):
    """Виджет для отображения списка файлов"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.double_click_callback = None
        self.folder_change_callback = None
        self.download_callback = None
        self.assign_tags_callback = None
        self.delete_callback = None
        self.preview_callback = None
        
        # Права доступа
        self.can_delete = False
        self.can_manage_tags = False
        
        self.create_widgets()
    
    def set_permissions(self, can_delete=False, can_manage_tags=False):
        """Устанавливает права доступа для контекстного меню"""
        self.can_delete = can_delete
        self.can_manage_tags = can_manage_tags
    
    def create_widgets(self):
        """Создаёт элементы интерфейса"""
        title = ttk.Label(self, text="Файлы и папки", font=('Arial', 10, 'bold'))
        title.pack(pady=5)
        
        columns = ('name', 'type', 'size', 'modified', 'tags')
        self.tree = ttk.Treeview(self, columns=columns, show='headings', height=20)
        
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
        
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<Button-3>', self.on_context_menu)
    
    def update_files(self, files):
        """Обновляет список файлов"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self._items_data = {}
        
        for f in files:
            item_type = 'Папка' if f.type == 'dir' else 'Файл'
            size = self._format_size(getattr(f, 'size', 0))
            modified = f.modified.strftime('%d.%m.%Y %H:%M') if hasattr(f, 'modified') else ''
            
            values = (f.name, item_type, size, modified, '')
            item_id = self.tree.insert('', tk.END, values=values)
            
            self._items_data[item_id] = {
                'name': f.name,
                'path': f.path,
                'type': f.type,
                'size': getattr(f, 'size', 0),
                'modified': modified,
                'resource_id': getattr(f, 'resource_id', None)
            }
    
    def update_tags_from_db(self):
        """Обновляет отображение тегов для всех файлов из БД"""
        from core.models import File
        
        for item_id, data in self._items_data.items():
            try:
                file_obj = File.objects.get(path=data.get('path'))
                tags_str = ", ".join([tag.name for tag in file_obj.tags.all()])
                self.tree.set(item_id, 'tags', tags_str)
            except File.DoesNotExist:
                pass
            except Exception as e:
                print(f"Ошибка обновления тегов: {e}")
    
    def _format_size(self, size):
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
    
    def get_selected_items(self):
        selected = []
        for item_id in self.tree.selection():
            if hasattr(self, '_items_data') and item_id in self._items_data:
                selected.append(self._items_data[item_id])
        return selected
    
    def on_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        if hasattr(self, '_items_data') and item_id in self._items_data:
            item = self._items_data[item_id]
            if self.double_click_callback:
                self.double_click_callback(item)
    
    def on_context_menu(self, event):
        """Показывает контекстное меню с учётом прав"""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        
        self.tree.selection_set(item_id)
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Скачать", command=self.on_download_selected)
        menu.add_command(label="Предпросмотр", command=self.on_preview_selected)
        menu.add_separator()
        
        # Назначить теги — только если есть права
        if self.can_manage_tags:
            menu.add_command(label="Назначить теги", command=self.on_assign_tags)
        
        # Удалить — только если есть права
        if self.can_delete:
            menu.add_separator()
            menu.add_command(label="Удалить", command=self.on_delete_selected)
        
        menu.post(event.x_root, event.y_root)
    
    def on_download_selected(self):
        selected = self.get_selected_items()
        if selected and self.download_callback:
            self.download_callback(selected[0])
    
    def on_preview_selected(self):
        selected = self.get_selected_items()
        if selected and self.preview_callback:
            self.preview_callback(selected[0])
    
    def on_assign_tags(self):
        selected = self.get_selected_items()
        if selected and self.assign_tags_callback:
            self.assign_tags_callback(selected[0])
    
    def on_delete_selected(self):
        selected = self.get_selected_items()
        if selected and self.delete_callback:
            self.delete_callback(selected[0])
    
    def bind_double_click(self, callback):
        self.double_click_callback = callback
    
    def bind_folder_change(self, callback):
        self.folder_change_callback = callback
    
    def bind_download(self, callback):
        self.download_callback = callback
    
    def bind_preview(self, callback):
        self.preview_callback = callback
    
    def bind_assign_tags(self, callback):
        self.assign_tags_callback = callback
    
    def bind_delete(self, callback):
        self.delete_callback = callback
