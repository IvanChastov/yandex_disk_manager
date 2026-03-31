import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import User
from core.yandex.storage import get_current_user


class SettingsDialog:
    """Диалог настроек приложения"""
    
    def __init__(self, parent, settings):
        self.parent = parent
        self.settings = settings
        self.result = None
        
        # Создаём окно - увеличиваем размер
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Настройки")
        self.dialog.geometry("550x600")  # было 800x600
        self.dialog.minsize(500, 500)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        self.load_current_settings()
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
        main = ttk.Frame(self.dialog, padding="15")
        main.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        ttk.Label(
            main,
            text="Настройки приложения",
            font=('Arial', 12, 'bold')
        ).pack(pady=(0, 15))
        
        # --- Настройки мониторинга ---
        monitor_frame = ttk.LabelFrame(main, text="Мониторинг", padding=10)
        monitor_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(monitor_frame, text="Интервал проверки (секунд):").pack(anchor=tk.W)
        
        interval_frame = ttk.Frame(monitor_frame)
        interval_frame.pack(fill=tk.X, pady=5)
        
        self.interval_var = tk.IntVar(value=300)
        interval_spinbox = ttk.Spinbox(
            interval_frame,
            from_=30,
            to=3600,
            increment=30,
            textvariable=self.interval_var,
            width=10
        )
        interval_spinbox.pack(side=tk.LEFT)
        
        ttk.Label(interval_frame, text="секунд (мин: 30, макс: 3600)").pack(side=tk.LEFT, padx=5)
        
        # --- Настройки уведомлений ---
        notifications_frame = ttk.LabelFrame(main, text="Уведомления", padding=10)
        notifications_frame.pack(fill=tk.X, pady=5)
        
        self.notify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            notifications_frame,
            text="Показывать всплывающие уведомления",
            variable=self.notify_var
        ).pack(anchor=tk.W)
        
        # --- Информация о пользователе ---
        user_frame = ttk.LabelFrame(main, text="Пользователь", padding=10)
        user_frame.pack(fill=tk.X, pady=5)
        
        current_user = get_current_user()
        ttk.Label(user_frame, text=f"Текущий пользователь: {current_user or 'не авторизован'}").pack(anchor=tk.W)
        
        # Кнопка смены пользователя
        ttk.Button(
            user_frame,
            text="Сменить пользователя",
            command=self.switch_user
        ).pack(anchor=tk.W, pady=5)
        
        # --- КНОПКИ ---
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=15)
        
        ttk.Button(
            btn_frame,
            text="Сохранить",
            command=self.on_save,
            width=12
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="Отмена",
            command=self.on_cancel,
            width=12
        ).pack(side=tk.RIGHT, padx=5)
    
    def load_current_settings(self):
        """Загружает текущие настройки"""
        if 'monitor_interval' in self.settings:
            self.interval_var.set(self.settings['monitor_interval'])
        if 'theme' in self.settings:
            self.theme_var.set(self.settings['theme'])
        if 'show_notifications' in self.settings:
            self.notify_var.set(self.settings['show_notifications'])
    
    def switch_user(self):
        """Смена пользователя"""
        from gui.auth_dialog import AuthDialog
        
        result = messagebox.askyesno(
            "Смена пользователя",
            "Для смены пользователя необходимо перезапустить приложение.\n\n"
            "Сначала получите новый токен, затем перезапустите программу.\n\n"
            "Продолжить?"
        )
        
        if result:
            dialog = AuthDialog(self.dialog)
            token = dialog.run()
            if token:
                messagebox.showinfo(
                    "Успех",
                    "Токен сохранён. Перезапустите приложение для вступления изменений в силу."
                )
    
    def on_save(self):
        """Сохраняет настройки"""
        self.result = {
            'monitor_interval': self.interval_var.get(),
            'show_notifications': self.notify_var.get()
        }
        self.dialog.destroy()
    
    def on_cancel(self):
        self.dialog.destroy()
    
    def run(self):
        self.dialog.wait_window()
        return self.result
