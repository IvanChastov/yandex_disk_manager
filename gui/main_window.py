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
    from tkinter import Tk

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настраиваем django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.yandex.client import YandexDiskClient
from core.yandex.storage import get_current_user, get_token_for_user
from core.yandex.monitor import DiskMonitor
from core.models import File, ChangeLog, Tag, User
from core.permissions import has_permission
from gui.auth_dialog import AuthDialog
from gui.widgets.file_list import FileListWidget
from gui.widgets.tag_panel import TagPanel
from gui.widgets.notifications import NotificationsWidget
from gui.tag_assign_dialog import TagAssignDialog
from gui.login_dialog import LoginDialog


class MainWindow:
    """Главное окно приложения"""

    def __init__(self):
        # Создаём окно с темой
        if USE_THEMES:
            self.root = ThemedTk(theme="radiance")
        else:
            self.root = Tk()
        
        self.root.title("Менеджер Яндекс.Диска")
        self.root.geometry("1300x750")
        self.root.minsize(900, 600)
        
        # Настраиваем закрытие ДО всего остального
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Настраиваем стили
        self.setup_styles()
        
        # Переменные
        self.client = None
        self.monitor = None
        self.current_user = None
        self.current_path = '/'
        
        # Права пользователя
        self.user_can_upload = False
        self.user_can_delete = False
        self.user_can_manage_tags = False

        # Создаём интерфейс
        self.create_menu()
        self.create_main_layout()
        self.create_status_bar()

        self.bind_hotkeys()

        # Показываем окно входа
        self.show_login()
        
        # Если пользователь не вошёл (окно закрыто), выходим
        if not self.current_user:
            self.root.destroy()
            return

        # История навигации (стек)
        self.navigation_history = []

        self.original_files = []

        saved_settings = self.load_settings_from_file()
        if saved_settings:
            self.apply_settings(saved_settings)
    
    def setup_styles(self):
        """Настраивает стили для всего приложения"""
        style = ttk.Style()
        style.theme_use(style.theme_use())
        style.configure('Treeview', rowheight=28)
        style.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))
        style.configure('Action.TButton', font=('Segoe UI', 9))
        style.configure('Title.TLabel', font=('Segoe UI', 10, 'bold'))
        style.configure('Status.TLabel', font=('Segoe UI', 9), foreground='gray')
        self.root.update_idletasks()

    def create_menu(self):
        """Создаёт главное меню"""
        menubar = tk.Menu(self.root)
        
        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Настройки", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.on_closing, accelerator="Ctrl+Q")
        menubar.add_cascade(label="Файл", menu=file_menu)

        # Меню "Диск"
        self.disk_menu = tk.Menu(menubar, tearoff=0)
        self.disk_menu.add_command(label="Обновить", command=self.refresh_files, accelerator="F5")
        self.disk_menu.add_command(label="Загрузить файл", command=self.upload_file)
        self.disk_menu.add_separator()
        self.disk_menu.add_command(label="Создать папку", command=self.create_folder)
        menubar.add_cascade(label="Диск", menu=self.disk_menu)

        # Меню "Вид"
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Показать теги", command=self.toggle_tags_panel)
        view_menu.add_command(label="Показать историю", command=self.toggle_history_panel)
        menubar.add_cascade(label="Вид", menu=view_menu)

        # Меню "Помощь"
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self.show_about)
        help_menu.add_command(label="Горячие клавиши", command=self.show_shortcuts)
        menubar.add_cascade(label="Помощь", menu=help_menu)

        # Меню "Админ" (всегда добавляем)
        admin_menu = tk.Menu(menubar, tearoff=0)
        admin_menu.add_command(label="Управление пользователями", command=self.show_admin_panel)
        admin_menu.add_separator()
        admin_menu.add_command(label="Сменить токен", command=self.change_token)
        menubar.add_cascade(label="Админ", menu=admin_menu)

        self.root.config(menu=menubar)

    def update_menu_permissions(self):
        """Обновляет состояние пунктов меню в зависимости от прав"""
        if hasattr(self, 'disk_menu'):
            # Индексы: 0-Обновить, 1-Загрузить файл, 2-разделитель, 3-Создать папку
            upload_state = tk.NORMAL if self.user_can_upload else tk.DISABLED
            try:
                self.disk_menu.entryconfig(1, state=upload_state)
                self.disk_menu.entryconfig(3, state=upload_state)
            except:
                pass

    def create_main_layout(self):
        """Создаёт основную компоновку (3 панели)"""
        main_container = ttk.Frame(self.root, padding="5")
        main_container.pack(fill=tk.BOTH, expand=True)
        
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

        # Навигационная панель
        nav_frame = ttk.Frame(center_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 5))

        self.back_button = ttk.Button(nav_frame, text="Назад", command=self.go_back, width=8)
        self.back_button.pack(side=tk.LEFT, padx=(0, 10))

        self.path_var = tk.StringVar()
        self.path_var.set("/")
        path_label = ttk.Label(nav_frame, textvariable=self.path_var, font=('Segoe UI', 9),
                               relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        refresh_button = ttk.Button(nav_frame, text="Обновить", command=self.refresh_files, width=8)
        refresh_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Строка поиска
        search_frame = ttk.Frame(center_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(search_frame, text="Поиск:", width=6).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.on_search())

        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.search_clear_button = ttk.Button(search_frame, text="X", command=self.clear_search, width=3)
        self.search_clear_button.pack(side=tk.RIGHT)

        self.search_tags_var = tk.BooleanVar()
        self.search_tags_check = ttk.Checkbutton(search_frame, text="По тегам",
                                                 variable=self.search_tags_var, command=self.on_search)
        self.search_tags_check.pack(side=tk.RIGHT, padx=(10, 0))

        self.search_name_var = tk.BooleanVar(value=True)
        self.search_name_check = ttk.Checkbutton(search_frame, text="По имени",
                                                  variable=self.search_name_var, command=self.on_search)
        self.search_name_check.pack(side=tk.RIGHT, padx=(10, 0))

        self.file_list = FileListWidget(center_frame)
        self.file_list.pack(fill=tk.BOTH, expand=True)
        
        # Передаём права в виджет списка файлов
        self.file_list.set_permissions(
            can_delete=self.user_can_delete,
            can_manage_tags=self.user_can_manage_tags
        )
        
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
        self.file_list.bind_download(self.download_file)
        self.file_list.bind_delete(self.on_delete_file)
        self.file_list.bind_preview(self.on_preview_file)

    def create_status_bar(self):
        """Создаёт строку состояния"""
        status_bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Готов")
        
        status_label = ttk.Label(status_bar, textvariable=self.status_var, anchor=tk.W, padding=(5, 2))
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.connection_var = tk.StringVar()
        self.connection_var.set("Не подключено")
        connection_label = ttk.Label(status_bar, textvariable=self.connection_var, padding=(5, 2))
        connection_label.pack(side=tk.RIGHT)
        
        hint_label = ttk.Label(status_bar, text="F5: обновить | Ctrl+F: поиск | Ctrl+D: скачать | Del: удалить",
                               padding=(5, 2), foreground="gray")
        hint_label.pack(side=tk.RIGHT, padx=10)

    def show_login(self):
        """Показывает окно входа"""
        from gui.login_dialog import LoginDialog
        
        dialog = LoginDialog(self.root)
        self.current_user = dialog.run()
        
        if not self.current_user:
            return
        
        role_display = {
            'admin': 'Администратор',
            'manager': 'Менеджер',
            'viewer': 'Наблюдатель',
        }.get(self.current_user.role, self.current_user.role)
        
        self.status_var.set(f"Пользователь: {self.current_user.username} ({role_display})")
        
        # Обновляем меню в зависимости от роли
        self.update_menu_for_role()
        
        # Загружаем корпоративный токен
        self.load_corporate_token()

    def load_corporate_token(self):
        """Загружает корпоративный токен из файла рядом с EXE"""
        import os
        import sys
        
        # Для EXE — путь к папке с EXE
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        
        token_file = os.path.join(base_dir, 'yandex_token.txt')
        
        print(f"DEBUG: Ищем токен в: {token_file}")
        
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                token = f.read().strip()
            if token:
                self.init_client_with_token(token)
                return True
        
        # Если токена нет, предлагаем администратору его ввести
        if self.current_user and self.current_user.role == 'admin':
            self.setup_corporate_token()
        else:
            self.status_var.set("Корпоративный токен не настроен. Обратитесь к администратору")
            self.connection_var.set("Не подключено")
        
        return False

    def setup_corporate_token(self):
        """Настройка корпоративного токена (только для администратора)"""
        token = simpledialog.askstring(
            "Настройка корпоративного токена",
            "Введите токен для доступа к корпоративному Яндекс.Диску:\n\n"
            "Как получить токен:\n"
            "1. Перейдите на https://oauth.yandex.ru/\n"
            "2. Создайте приложение\n"
            "3. Получите токен через авторизацию\n\n"
            "Токен будет сохранён в файл yandex_token.txt",
            parent=self.root,
            show="*"
        )

        if token:
            token_file = os.path.join(os.path.dirname(__file__),
                                      '..',
                                      'yandex_token.txt'
                                      )
            with open(token_file, 'w') as f:
                f.write(token.strip())
            messagebox.showinfo("Успех",
                                "Токен сохранён. Перезапустите приложение"
                                )
            self.root.destroy() # Закрываем приложение для перезапуска

    def init_client_with_token(self, token):
        """Инициализирует клиент с переданным токеном"""
        try:
            self.client = YandexDiskClient(token=token)
            self.status_var.set("Подключено к корпоративному Яндекс.Диску")
            self.connection_var.set("Подключено")
            self.refresh_files()
            self.start_monitor()
            return True
        except Exception as e:
            self.status_var.set(f"Ошибка подключения: {e}")
            self.connection_var.set("Ошибка")
            return False

    def update_menu_for_role(self):
        """Обновляет меню в зависимости от роли пользователя"""
        if not self.current_user:
            return
        
        role = self.current_user.role

        # Права доступа
        self.user_can_upload = role in ['admin', 'manager']
        self.user_can_delete = role == 'admin'
        self.user_can_manage_tags = role in ['admin', 'manager']

        # Обновляем состояние пунктов меню
        self.update_menu_permissions()

    def show_admin_panel(self):
        """Показывает панель администратора"""
        if self.current_user and self.current_user.role == 'admin':
            from gui.admin_dialog import AdminDialog
            AdminDialog(self.root)
        else:
            messagebox.showerror("Ошибка", "У вас нет прав для доступа к админ-панели")

    def start_monitor(self):
        """Запускает фоновый мониторинг"""
        if self.monitor:
            self.monitor.stop()

        try:
            # Получаем корпоративный токен из файла
            token_file = os.path.join(os.path.dirname(__file__), '..', 'yandex_token.txt')
            corporate_token = None
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    corporate_token = f.read().strip()
            
            self.monitor = DiskMonitor(
                username=None,
                check_interval=300,
                on_change_callback=self.on_monitor_change,
                corporate_token=corporate_token  # передаём токен напрямую
            )
            self.monitor.start()
            print("Мониторинг запущен")
        except Exception as e:
            print(f"Ошибка запуска мониторинга: {e}")

    def on_monitor_change(self):
        """Вызывается при обнаружении изменений мониторингом"""
        self.notifications.refresh()
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
            self.file_list.update_tags_from_db()
            self.status_var.set(f"Загружено {len(self.original_files)} элементов")
        except Exception as e:
            self.status_var.set(f"Ошибка загрузки: {e}")

    def upload_file(self):
        """Загружает файл на диск"""
        if not self.user_can_upload:
            self.status_var.set("У вас нет прав на загрузку файлов")
            return
            
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
            self.notifications.refresh()
        else:
            self.status_var.set(f"Ошибка загрузки {file_name}")

    def create_folder(self):
        """Создаёт новую папку"""
        if not self.user_can_upload:
            self.status_var.set("У вас нет прав на создание папок")
            return
            
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
            self.navigation_history.append(self.current_path)
            self.current_path = item.get('path')
            self.update_path_display()
            self.refresh_files()
        else:
            self.download_file(item)

    def on_folder_change(self, path):
        """Обработка смены папки"""
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
        if not self.user_can_manage_tags:
            self.status_var.set("У вас нет прав на управление тегами")
            return
            
        file_path = file_item.get('path')
        file_name = file_item.get('name')
        
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
            self.notifications.refresh()
            self.status_var.set(f"Теги для {file_name} обновлены")

    def on_delete_file(self, file_item):
        """Удаляет файл с диска"""
        if not self.user_can_delete:
            self.status_var.set("У вас нет прав на удаление файлов")
            return
            
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
            self.notifications.refresh()
        else:
            self.status_var.set(f"Ошибка удаления {file_name}")

    def go_back(self):
        """Возвращает на предыдущую папку"""
        if self.navigation_history:
            previous_path = self.navigation_history.pop()
            self.current_path = previous_path
            self.update_path_display()
            self.refresh_files()
        else:
            self.status_var.set("Нет предыдущей папки")

    def change_token(self):
        """Смена корпоративного токена (только для администратора)"""
        if not (self.current_user and self.current_user.role == 'admin'):
            messagebox.showerror("Ошибка", "У вас нет прав для смены токена")
            return
        
        from tkinter import simpledialog, messagebox
        import os
        
        token = simpledialog.askstring(
            "Смена токена",
            "Введите новый токен для доступа к Яндекс.Диску:\n\n"
            "Токен будет сохранён в файл yandex_token.txt\n"
            "После сохранения приложение перезапустится.",
            parent=self.root,
            show='*'
        )
        
        if token:
            token_file = os.path.join(os.path.dirname(__file__), '..', 'yandex_token.txt')
            with open(token_file, 'w') as f:
                f.write(token.strip())
            messagebox.showinfo("Успех", "Токен сохранён. Перезапустите приложение.")
            self.root.destroy()
            
    def update_path_display(self):
        """Обновляет отображение текущего пути"""
        display_path = self.current_path
        if display_path.startswith('disk:'):
            display_path = display_path[5:] or '/'
        if not display_path:
            display_path = '/'
        self.path_var.set(display_path)

    def toggle_tags_panel(self):
        pass

    def toggle_history_panel(self):
        pass

    def show_about(self):
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
                
                if self.search_name_var.get() and query.lower() in f.name.lower():
                    match = True
                
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
        if hasattr(self, 'search_var'):
            self.search_var.set("")
        self.refresh_files()

    def on_closing(self):
        """Обработка закрытия окна"""
        if self.monitor:
            self.monitor.stop()

        if messagebox.askokcancel("Выход", "Закрыть приложение?"):
            self.root.destroy()

    def bind_hotkeys(self):
        """Привязывает горячие клавиши"""
        self.root.bind_all('<Key>', self.on_key_press)
        self.root.bind_all('<F5>', lambda e: self.refresh_files())
        self.root.bind_all('<Delete>', lambda e: self.delete_selected())

    def on_key_press(self, event):
        """Обрабатывает нажатия клавиш"""
        if event.state & 0x4:
            keysym = event.keysym
            keysym_num = event.keysym_num
            
            if keysym == 'f' or keysym_num == 102 or keysym_num == 1072:
                self.focus_search()
                return "break"
            elif keysym == 'd' or keysym_num == 100 or keysym_num == 1074:
                self.download_selected()
                return "break"
            elif keysym == 'r' or keysym_num == 114 or keysym_num == 1082:
                self.refresh_files()
                return "break"
            elif keysym == 'q' or keysym_num == 113 or keysym_num == 1081:
                self.on_closing()
                return "break"
        
        if event.keysym == 'F5' or event.keysym_num == 65474:
            self.refresh_files()
            return "break"
        
        if event.keysym == 'Delete' or event.keysym_num == 65535:
            self.delete_selected()
            return "break"
        
        if event.keysym == 'Escape' or event.keysym_num == 65307:
            self.clear_search()
            return "break"
        
        return None

    def focus_search(self):
        """Устанавливает фокус на поле поиска"""
        if hasattr(self, 'search_entry'):
            self.search_entry.focus_set()
            self.search_entry.select_range(0, tk.END)
            self.status_var.set("Поиск (Ctrl+F для фокуса)")

    def download_selected(self):
        """Скачивает выбранный файл"""
        selected = self.file_list.get_selected_items()
        if not selected:
            self.status_var.set("Нет выбранного файла для скачивания")
            return
        
        file_item = selected[0]
        if file_item.get('type') == 'dir':
            self.status_var.set("Скачивание папок не поддерживается")
            return
        
        self.download_file(file_item)

    def delete_selected(self):
        """Удаляет выбранный файл"""
        selected = self.file_list.get_selected_items()
        if not selected:
            self.status_var.set("Нет выбранного файла для удаления")
            return
        
        self.on_delete_file(selected[0])

    def show_shortcuts(self):
        shortcuts_text = """
Горячие клавиши:

F5              - Обновить список файлов
Ctrl + R        - Обновить список файлов

Ctrl + F        - Перейти к поиску

Ctrl + D        - Скачать выбранный файл
Delete (Del)    - Удалить выбранный файл

Ctrl + Q        - Выход из приложения

В контекстном меню файла:
    - Скачать
    - Предпросмотр
    - Назначить теги (только Manager и Admin)
    - Удалить (только Admin)
"""
        messagebox.showinfo("Горячие клавиши", shortcuts_text)

    def show_settings(self):
        """Показывает окно настроек"""
        from gui.settings_dialog import SettingsDialog
        
        current_settings = {
            'monitor_interval': self.monitor.check_interval if self.monitor else 300,
            'show_notifications': True
        }
        
        dialog = SettingsDialog(self.root, current_settings)
        new_settings = dialog.run()
        
        if new_settings:
            self.apply_settings(new_settings)

    def apply_settings(self, settings):
        """Применяет новые настройки"""
        
        # Интервал мониторинга
        if self.monitor and settings['monitor_interval'] != self.monitor.check_interval:
            self.monitor.check_interval = settings['monitor_interval']
            self.status_var.set(f"Интервал мониторинга изменён на {settings['monitor_interval']} секунд")
        
        # Сохраняем настройки в файл
        self.save_settings_to_file(settings)

    def save_settings_to_file(self, settings):
        import json
        settings_file = os.path.join(os.path.dirname(__file__), 'settings.json')
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            print(f"Настройки сохранены в {settings_file}")
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")

    def load_settings_from_file(self):
        import json
        settings_file = os.path.join(os.path.dirname(__file__), 'settings.json')
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                return settings
            except Exception as e:
                print(f"Ошибка загрузки настроек: {e}")
        return None

    def run(self):
        self.root.mainloop()

    def on_preview_file(self, file_item):
        from gui.preview_dialog import PreviewDialog
        
        if file_item.get('type') == 'dir':
            self.status_var.set("Предпросмотр папок не поддерживается")
            return
        
        dialog = PreviewDialog(self.root, file_item)
        dialog.run()


if __name__ == "__main__":
    app = MainWindow()
    app.run()
