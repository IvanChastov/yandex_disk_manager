import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sys
import os
import threading

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
from gui.auth_dialog import AuthDialog
from gui.widgets.file_list import FileListWidget
from gui.widgets.tag_panel import TagPanel
from gui.widgets.notifications import NotificationsWidget


class MainWindow:
    """Главное окно приложения"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Менеджер Яндекс.Диска")
        self.root.geometry("1200x700")
        self.root.minsize(800, 500)

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

        # Настраиваем закрытие
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_menu(self):
        """Создаёт главное меню"""
        menubar = tk.Menu(self.root)

        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="Авторизация",
            command=self.show_auth_dialog
            )
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.on_closing)
        menubar.add_cascade(label="Файл", menu=file_menu)

        # Меню "Диск"
        disk_menu = tk.Menu(menubar, tearoff=0)
        disk_menu.add_command(label="Обновить", command=self.refresh_files)
        disk_menu.add_command(label="Загрузить файл", command=self.upload_file)
        disk_menu.add_separator()
        disk_menu.add_command(
            label="Создать папку",
            command=self.create_folder
            )
        menubar.add_cascade(label="Диск", menu=disk_menu)

        # Меню "Вид"
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(
            label="Показать теги",
            command=self.toggle_tags_panel
            )
        view_menu.add_command(
            label="Показать историю",
            command=self.toggle_history_panel
            )
        menubar.add_cascade(
            label="Вид",
            menu=view_menu
            )

        # Меню "Помощь"
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label="О программе",
            command=self.show_about
        )
        menubar.add_cascade(label="Помощь", menu=help_menu)

        self.root.config(menu=menubar)

    def create_main_layout(self):
        """Создаёт основную компоновку (3 панели)"""
        # Создаём PanedWindow для разделения панелей
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Левая панель (теги)
        left_frame = ttk.Frame(self.main_paned, relief=tk.SUNKEN, borderwidth=1)
        left_frame.pack_propagate(False)
        left_frame.configure(width=200)

        left_title = ttk.Label(left_frame, text="Теги", font=('Arial', 10, 'bold'))
        left_title.pack(pady=5)

        self.tag_panel = TagPanel(left_frame)
        self.tag_panel.pack(fill=tk.BOTH, expand=True)
        self.main_paned.add(left_frame, weight=1)

        # Центральная панель (список файлов)
        center_frame = ttk.Frame(self.main_paned, relief=tk.SUNKEN, borderwidth=1)
        center_frame.pack_propagate(False)

        center_title = ttk.Label(center_frame, text="Файлы и папки", font=('Arial', 10, 'bold'))
        center_title.pack(pady=5)

        self.file_list = FileListWidget(center_frame)
        self.file_list.pack(fill=tk.BOTH, expand=True)
        self.main_paned.add(center_frame, weight=3)

        # Правая панель (история изменений)
        right_frame = ttk.Frame(self.main_paned, relief=tk.SUNKEN, borderwidth=1)
        right_frame.pack_propagate(False)
        right_frame.configure(width=280)

        right_title = ttk.Label(right_frame, text="История изменений", font=('Arial', 10, 'bold'))
        right_title.pack(pady=5)

        self.notifications = NotificationsWidget(right_frame)
        self.notifications.pack(fill=tk.BOTH, expand=True)
        self.main_paned.add(right_frame, weight=1)

        # Привязываем обработчики
        self.file_list.bind_double_click(self.on_file_double_click)
        self.file_list.bind_folder_change(self.on_folder_change)

        # Обновляем геометрию (без paneconfig)
        self.root.update_idletasks()

    def create_status_bar(self):
        """Создаёт строку состояния"""
        self.status_var = tk.StringVar()
        self.status_var.set("Готов")

        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

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
        else:
            self.status_var.set(
                "Пользователь не найден. Создайте пользователя в админке"
                )

    def init_client(self, token):
        """Инициализирует клиент и загружает данные"""
        try:
            self.client = YandexDiskClient(
                token=token,
                username=self.current_user
                )
            self.status_var.set("Подключено к Яндекс.Диску")
            self.refresh_files()
            self.start_monitor()
        except Exception as e:
            self.status_var.set(f"Ошибка подключения: {e}")

    def start_monitor(self):
        """Запускает фоновый мониторинг"""
        if self.monitor:
            self.monitor.stop()

        try:
            self.monitor = DiskMonitor(
                username=self.current_user,
                check_interval=300
            )
            self.monitor.start()
            print("Монитор запущен")
        except Exception as e:
            print(f"Ошибка запуска мониторинга: {e}")

    def refresh_files(self):
        """Обновляет список файлов в текущей папке"""
        if not self.client:
            self.status_var.set("Клиент не инициализирован. Авторизуйтесь")
            return

        self.status_var.set("Загрузка списка файлов...")
        self.root.update()

        try:
            files = self.client.get_files_list(self.current_path)
            self.file_list.update_files(files)
            self.status_var.set(f"Загружено {len(files)} элементов")
        except Exception as e:
            self.status_var.set(f"Ошибка загрузки: {e}")

    def show_auth_dialog(self):
        """Показывает диалог авторизации"""
        dialog = AuthDialog(self.root)
        token = dialog.run()

        if token:
            self.init_client(token)

    def upload_file(self):
        """Загружает файл на диск"""
        file_path = filedialog.askopenfilename(
            title="Выберите файл для загрузки"
            )
        if not file_path:
            return

        if not self.client:
            self.status_var.set("Клиент не инициализирован")
            return

        file_name = os.path.basename(file_path)
        remote_path = os.path.join(
            self.current_path, file_name).replace('\\', '/')

        self.status_var.set(f"Загрузка {file_name}...")
        self.root.update()

        success = self.client.upload_file(file_path, remote_path)

        if success:
            self.status_var.set(f"Файл {file_name} загружен")
            self.refresh_files()
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

        remote_path = os.path.join(
            self.current_path, folder_name).replace('\\', '/')

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
            # Переходим в папку
            self.current_path = item.get('path')
            self.refresh_files()
        else:
            # Скачиваем файл
            self.download_file(item)

    def on_folder_change(self, path):
        """Обработка смены папки"""
        self.current_path = path
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

    def toggle_tags_panel(self):
        """Показывает/скрывает панель тегов"""
        # TODO: реализовать
        pass

    def toggle_history_panel(self):
        """Показывает/скрывает панель истории"""
        # TODO: реализовать
        pass

    def show_about(self):
        """Показывает информацию о программе"""
        messagebox.showinfo(
            "О программе",
            "Менеджер Яндекс.Диска\n"
            "Версия 1.0\n\n"
            "Приложения для управления файлами на Яндекс.Диске\n"
            "с поддержкой мониторига изменений и системы тегов.\n\n"
            "Разработано в рамках ВКР"
        )

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
