import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sys
import os
import threading

# Подключаем ttkthemes
try:
    from ttkthemes import ThemedTk
    USE_THEMES = True
except ImportError:
    USE_THEMES = False
    print("Для улучшенного интерфейса установите: pip install ttkthemes")
    # Если не установлено, используем обычный Tk
    from tkinter import Tk as ThemedTk

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настраиваем django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.yandex.client import YandexDiskClient
from core.yandex.storage import get_current_user, get_token_for_user
from core.yandex.monitor import DiskMonitor
from core.models import File, ChangeLog, Tag
from core.permissions import has_permission
from gui.auth_dialog import AuthDialog
from gui.widgets.file_list import FileListWidget
from gui.widgets.tag_panel import TagPanel
from gui.widgets.notifications import NotificationsWidget
from gui.tag_assign_dialog import TagAssignDialog


class MainWindow:
    """Главное окно приложения"""

    def __init__(self):
        # Создаём окно с темой
        if USE_THEMES:
            self.root = ThemedTk(theme="radiance")  # Доступные темы: arc, breeze, equilux, plastik, radiance, ubuntu
        else:
            self.root = ThemedTk()
        
        self.root.title("Менеджер Яндекс.Диска")
        self.root.geometry("1300x750")
        self.root.minsize(900, 600)
        
        # Настраиваем стили
        self.setup_styles()
        
        # Переменные
        self.client = None
        self.monitor = None
        self.current_user = None
        self.current_path = '/'

        # Создаём интерфейс
        self.create_menu()
        self.create_main_layout()
        self.create_status_bar()

        # Загружаем данные
        self.load_user()

        # История навигации (стек)
        self.navigation_history = []

        self.original_files = []  # Для хранения оригинального списка файлов

        # Настраиваем закрытие
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_styles(self):
        """Настраивает стили для всего приложения"""
        style = ttk.Style()
        
        # Настройка Treeview (увеличиваем высоту строк)
        style.configure('Treeview', rowheight=28)
        style.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))
        
        # Настройка кнопок
        style.configure('Action.TButton', font=('Segoe UI', 9))
        
        # Настройка заголовков
        style.configure('Title.TLabel', font=('Segoe UI', 10, 'bold'))
        
        # Если используется ThemedTk, можно дополнительно настроить
        if USE_THEMES:
            try:
                current_theme = self.root.get_theme()
                if current_theme == "equilux":
                    # Дополнительные настройки для темной темы
                    style.configure('Status.TLabel', font=('Segoe UI', 9), foreground='#aaaaaa')
            except:
                pass

    def create_menu(self):
        """Создаёт главное меню"""
        menubar = tk.Menu(self.root)
        
        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Авторизация", command=self.show_auth_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.on_closing)
        menubar.add_cascade(label="Файл", menu=file_menu)

        # Меню "Диск"
        disk_menu = tk.Menu(menubar, tearoff=0)
        disk_menu.add_command(label="Обновить", command=self.refresh_files)
        disk_menu.add_command(label="Загрузить файл", command=self.upload_file)
        disk_menu.add_separator()
        disk_menu.add_command(label="Создать папку", command=self.create_folder)
        menubar.add_cascade(label="Диск", menu=disk_menu)

        # Меню "Вид"
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Показать теги", command=self.toggle_tags_panel)
        view_menu.add_command(label="Показать историю", command=self.toggle_history_panel)
        menubar.add_cascade(label="Вид", menu=view_menu)

        # Меню "Помощь"
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Помощь", menu=help_menu)

        self.root.config(menu=menubar)

    def create_main_layout(self):
        """Создаёт основную компоновку (3 панели)"""
        # Основной контейнер с отступами
        main_container = ttk.Frame(self.root, padding="5")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Создаём PanedWindow для разделения панелей
        self.main_paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Левая панель (теги)
        left_frame = ttk.LabelFrame(self.main_paned, text=" Теги ", padding=5)
        left_frame.pack_propagate(False)
        left_frame.configure(width=220)
        
        self.tag_panel = TagPanel(left_frame)
        self.tag_panel.set_main_window(self)
        self.tag_panel.pack(fill=tk.BOTH, expand=True)
        self.main_paned.add(left_frame, weight=1)
        
        # Центральная панель (список файлов)
        center_frame = ttk.LabelFrame(self.main_paned, text=" Файлы и папки ", padding=5)
        center_frame.pack_propagate(False)

        # --- НАВИГАЦИОННАЯ ПАНЕЛЬ ---
        nav_frame = ttk.Frame(center_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 5))

        # Кнопка "Назад"
        self.back_button = ttk.Button(
            nav_frame,
            text="Назад",
            command=self.go_back,
            width=8
        )
        self.back_button.pack(side=tk.LEFT, padx=(0, 10))

        # Отображение текущего пути
        self.path_var = tk.StringVar()
        self.path_var.set("/")

        path_label = ttk.Label(
            nav_frame,
            textvariable=self.path_var,
            font=('Segoe UI', 9),
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Кнопка "Обновить"
        refresh_button = ttk.Button(
            nav_frame,
            text="Обновить",
            command=self.refresh_files,
            width=8
        )
        refresh_button.pack(side=tk.RIGHT, padx=(5, 0))
        # --- КОНЕЦ НАВИГАЦИОННОЙ ПАНЕЛИ ---

        # --- СТРОКА ПОИСКА  ---
        search_frame = ttk.Frame(center_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(search_frame, text="Поиск:", width=6).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.on_search())  # Вызываем при каждом изменении

        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Кнопка сброса поиска
        self.search_clear_button = ttk.Button(
            search_frame,
            text="X",
            command=self.clear_search,
            width=3
        )
        self.search_clear_button.pack(side=tk.RIGHT)

        # Чекбокс "Поиск по тегам"
        self.search_tags_var = tk.BooleanVar()
        self.search_tags_check = ttk.Checkbutton(
            search_frame,
            text="По тегам",
            variable=self.search_tags_var,
            command=self.on_search
        )
        self.search_tags_check.pack(side=tk.RIGHT, padx=(10, 0))

        # Чекбокс "Поиск по имени"
        self.search_name_var = tk.BooleanVar(value=True)
        self.search_name_check = ttk.Checkbutton(
            search_frame,
            text="По имени",
            variable=self.search_name_var,
            command=self.on_search
        )
        self.search_name_check.pack(side=tk.RIGHT, padx=(10, 0))
        # --- КОНЕЦ СТРОКИ ПОИСКА ---

        self.file_list = FileListWidget(center_frame)
        self.file_list.pack(fill=tk.BOTH, expand=True)
        self.main_paned.add(center_frame, weight=3)
        
        # Правая панель (история изменений)
        right_frame = ttk.LabelFrame(self.main_paned, text=" История изменений ", padding=5)
        right_frame.pack_propagate(False)
        right_frame.configure(width=280)
        
        self.notifications = NotificationsWidget(right_frame)
        self.notifications.pack(fill=tk.BOTH, expand=True)
        self.main_paned.add(right_frame, weight=1)
        
        # Привязываем обработчики
        self.file_list.bind_double_click(self.on_file_double_click)
        self.file_list.bind_folder_change(self.on_folder_change)
        self.file_list.bind_assign_tags(self.on_assign_tags)
        self.file_list.bind_delete(self.on_delete_file)

    def create_status_bar(self):
        """Создаёт строку состояния"""
        status_bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Готов")
        
        status_label = ttk.Label(
            status_bar,
            textvariable=self.status_var,
            anchor=tk.W,
            padding=(5, 2)
        )
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Индикатор подключения (обновляется при авторизации)
        self.connection_var = tk.StringVar()
        self.connection_var.set("● Не подключено")
        
        connection_label = ttk.Label(
            status_bar,
            textvariable=self.connection_var,
            padding=(5, 2)
        )
        connection_label.pack(side=tk.RIGHT)

    def load_user(self):
        """Загружает текущего пользователя"""
        username = get_current_user()
        if username:
            self.current_user = username
            self.status_var.set(f"Пользователь: {username}")

            # Проверяем наличие токена
            token = get_token_for_user(username)
            if token:
                self.init_client(token)
            else:
                self.status_var.set("Нет токена. Нажмите Файл -> Авторизация")
                self.connection_var.set("● Не авторизован")
        else:
            self.status_var.set("Пользователь не найден. Создайте пользователя в админке")
            self.connection_var.set("● Ошибка")

    def init_client(self, token):
        """Инициализирует клиент и загружает данные"""
        try:
            self.client = YandexDiskClient(token=token, username=self.current_user)
            self.status_var.set("Подключено к Яндекс.Диску")
            self.connection_var.set("● Подключено")
            self.refresh_files()
            self.start_monitor()
        except Exception as e:
            self.status_var.set(f"Ошибка подключения: {e}")
            self.connection_var.set("● Ошибка")

    def show_auth_dialog(self):
        """Показывает диалог авторизации"""
        dialog = AuthDialog(self.root)
        token = dialog.run()

        if token:
            self.init_client(token)

    def start_monitor(self):
        """Запускает фоновый мониторинг"""
        if self.monitor:
            self.monitor.stop()

        try:
            self.monitor = DiskMonitor(
                username=self.current_user,
                check_interval=300,
                on_change_callback=self.on_monitor_change  # Добавляем коллбэк
            )
            self.monitor.start()
            print("Мониторинг запущен")
        except Exception as e:
            print(f"Ошибка запуска мониторинга: {e}")

    def on_monitor_change(self):
        """Вызывается при обнаружении изменений мониторингом"""
        # Обновляем ленту изменений в GUI
        self.notifications.refresh()
        # Обновляем список файлов (если нужно)
        self.refresh_files()

    def refresh_files(self):
        """Обновляет список файлов в текущей папке"""
        if not self.client:
            self.status_var.set("Клиент не инициализирован. Авторизуйтесь")
            return

        self.status_var.set("Загрузка списка файлов...")
        self.root.update()
        
        self.update_path_display()

        try:
            self.original_files = self.client.get_files_list(self.current_path)
            self.file_list.update_files(self.original_files)
            
            # Обновляем теги из БД
            self.file_list.update_tags_from_db()
            
            self.status_var.set(f"Загружено {len(self.original_files)} элементов")
        except Exception as e:
            self.status_var.set(f"Ошибка загрузки: {e}")

    def upload_file(self):
        """Загружает файл на диск"""
        file_path = filedialog.askopenfilename(title="Выберите файл для загрузки")
        if not file_path:
            return

        if not self.client:
            self.status_var.set("Клиент не инициализирован")
            return

        file_name = os.path.basename(file_path)
        remote_path = os.path.join(self.current_path, file_name).replace('\\', '/')

        self.status_var.set(f"Загрузка {file_name}...")
        self.root.update()

        success = self.client.upload_file(file_path, remote_path)

        if success:
            self.status_var.set(f"Файл {file_name} загружен")
            self.refresh_files()
            print("DEBUG: Вызываем notifications.refresh() из upload_file")
            self.notifications.refresh()
            
            # Проверяем, что запись появилась в ChangeLog
            from core.models import ChangeLog
            latest = ChangeLog.objects.all().order_by('-changed_at')[:1]
            if latest:
                print(f"DEBUG: Последнее изменение: {latest[0].change_type} - {latest[0].file_path}")
            else:
                print("DEBUG: Нет записей в ChangeLog")
            
            self.notifications.refresh()
        else:
            self.status_var.set(f"Ошибка загрузки {file_name}")

    def create_folder(self):
        """Создаёт новую папку"""
        folder_name = simpledialog.askstring(
            "Создать папку",
            "Введите название папки:",
            parent=self.root
        )

        if not folder_name:
            return

        if not self.client:
            self.status_var.set("Клиент не инициализирован")
            return

        remote_path = os.path.join(self.current_path, folder_name).replace('\\', '/')

        self.status_var.set(f"Создание папки {folder_name}...")
        self.root.update()

        success = self.client.create_folder(remote_path)

        if success:
            self.status_var.set(f"Папка {folder_name} создана")
            self.refresh_files()
        else:
            self.status_var.set(f"Ошибка создания папки {folder_name}")

    def on_file_double_click(self, item):
        """Обработка двойного клика по файлу/папке"""
        if item.get('type') == 'dir':
            # Сохраняем текущий путь в историю
            self.navigation_history.append(self.current_path)
            self.current_path = item.get('path')
            self.update_path_display()
            self.refresh_files()
        else:
            self.download_file(item)

    def on_folder_change(self, path):
        """Обработка смены папки (например, из списка)"""
        self.navigation_history.append(self.current_path)
        self.current_path = path
        self.update_path_display()
        self.refresh_files()

    def download_file(self, item):
        """Скачивает файл"""
        file_name = item.get('name')
        remote_path = item.get('path')

        save_path = filedialog.asksaveasfilename(
            title="Сохранить файл как",
            initialfile=file_name,
            defaultextension=os.path.splitext(file_name)[1]
        )

        if not save_path:
            return

        if not self.client:
            self.status_var.set("Клиент не инициализирован")
            return

        self.status_var.set(f"Скачивание {file_name}...")
        self.root.update()

        success = self.client.download_file(remote_path, save_path)

        if success:
            self.status_var.set(f"Файл {file_name} скачан")
        else:
            self.status_var.set(f"Ошибка скачивания {file_name}")

    def on_assign_tags(self, file_item):
        """Назначает теги файлу"""
        file_path = file_item.get('path')
        file_name = file_item.get('name')
        
        # Получаем текущие теги файла из БД
        try:
            file_obj = File.objects.get(path=file_path)
            current_tags = [tag.name for tag in file_obj.tags.all()]
        except File.DoesNotExist:
            import django.utils.timezone
            file_obj = File.objects.create(
                yandex_id=file_item.get('resource_id', ''),
                name=file_name,
                path=file_path,
                type=file_item.get('type', 'file'),
                size=file_item.get('size', 0),
                created_at=django.utils.timezone.now(),
                modified_at=django.utils.timezone.now(),
            )
            current_tags = []

        # Показываем диалог
        dialog = TagAssignDialog(self.root, file_path, current_tags)
        selected_tags = dialog.run()
        
        if selected_tags is not None:
            file_obj.tags.clear()
            for tag_name in selected_tags:
                try:
                    tag = Tag.objects.get(name=tag_name)
                    file_obj.tags.add(tag)
                except Tag.DoesNotExist:
                    pass
            
            self.file_list.update_tags_from_db()
            self.notifications.refresh()  # Обновляем ленту после изменения тегов
            self.status_var.set(f"Теги для {file_name} обновлены")

    def on_delete_file(self, file_item):
        """Удаляет файл с диска"""
        file_name = file_item.get('name')
        remote_path = file_item.get('path')
        
        if not messagebox.askyesno("Подтверждение", f"Удалить файл '{file_name}'?"):
            return
        
        if not self.client:
            self.status_var.set("Клиент не инициализирован")
            return
        
        self.status_var.set(f"Удаление {file_name}...")
        self.root.update()
        
        success = self.client.delete_file(remote_path)
        
        if success:
            self.status_var.set(f"Файл {file_name} удалён")
            self.refresh_files()
            print("DEBUG: Вызываем notifications.refresh() из on_delete_file")
            self.notifications.refresh()
        else:
            self.status_var.set(f"Ошибка удаления {file_name}")

    def go_back(self):
        """Возвращает на предыдущую папку"""
        if self.navigation_history:
            # Берём последний путь из истории
            previous_path = self.navigation_history.pop()
            self.current_path = previous_path
            self.update_path_display()
            self.refresh_files()
        else:
            self.status_var.set("Нет предыдущей папки")
            
    def update_path_display(self):
        """Обновляет отображение текущего пути"""
        # Преобразуем путь в читаемый вид
        display_path = self.current_path
        if display_path.startswith('disk:'):
            display_path = display_path[5:] or '/'
        if not display_path:
            display_path = '/'
        self.path_var.set(display_path)

    def toggle_tags_panel(self):
        """Показывает/скрывает панель тегов"""
        pass

    def toggle_history_panel(self):
        """Показывает/скрывает панель истории"""
        pass

    def show_about(self):
        """Показывает информацию о программе"""
        messagebox.showinfo(
            "О программе",
            "Менеджер Яндекс.Диска\n"
            "Версия 1.0\n\n"
            "Приложение для управления файлами на Яндекс.Диске\n"
            "с поддержкой мониторинга изменений и системы тегов.\n\n"
            "Разработано в рамках ВКР"
        )

    def on_search(self):
        """Вызывается при изменении поискового запроса"""
        query = self.search_var.get().strip()
        
        if not query:
            self.clear_search()
            return
        
        if not self.original_files:
            return
        
        self.status_var.set(f"Поиск: {query}...")
        self.root.update()
        
        try:
            filtered_files = []
            for f in self.original_files:
                match = False
                
                # Поиск по имени
                if self.search_name_var.get() and query.lower() in f.name.lower():
                    match = True
                
                # Поиск по тегам
                if not match and self.search_tags_var.get():
                    try:
                        from core.models import File as FileModel
                        file_obj = FileModel.objects.get(path=f.path)
                        tags = [tag.name.lower() for tag in file_obj.tags.all()]
                        if any(query.lower() in tag for tag in tags):
                            match = True
                    except FileModel.DoesNotExist:
                        pass
                
                if match:
                    filtered_files.append(f)
            
            self.file_list.update_files(filtered_files)
            self.status_var.set(f"Найдено {len(filtered_files)} из {len(self.original_files)} элементов")
            
        except Exception as e:
            self.status_var.set(f"Ошибка поиска: {e}")

    def clear_search(self):
        """Сбрасывает поиск"""
        self.search_var.set("")
        self.refresh_files()

    def on_closing(self):
        """Обработка закрытия окна"""
        if self.monitor:
            self.monitor.stop()

        if messagebox.askokcancel("Выход", "Закрыть приложение?"):
            self.root.destroy()

    def run(self):
        """Запускает главный цикл приложения"""
        self.root.mainloop()


if __name__ == "__main__":
    app = MainWindow()
    app.run()
