import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import User
from django.contrib.auth import authenticate


class LoginDialog:
    """Диалог входа в приложение"""

    def __init__(self, parent):
        self.parent = parent
        self.user = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Вход в систему")
        self.dialog.geometry("600x500")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.create_widgets()
        self.center_window()

    def center_window(self):
        self.dialog.update_idletasks()
        w = self.dialog.winfo_width()
        h = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f'{w}x{h}+{x}+{y}')

    def create_widgets(self):
        main = ttk.Frame(self.dialog, padding="20")
        main.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        ttk.Label(
            main,
            text="Менеджер Яндекс.Диска",
            font=('Arial', 14, 'bold')
        ).pack(pady=(0, 20))

        # Логин
        ttk.Label(main, text="Логин:").pack(anchor=tk.W)
        self.username_entry = ttk.Entry(main, width=30)
        self.username_entry.pack(fill=tk.X, pady=(0, 10))

        # Пароль
        ttk.Label(main, text="Пароль:").pack(anchor=tk.W)
        self.password_entry = ttk.Entry(main, show="*", width=30)
        self.password_entry.pack(fill=tk.X, pady=(0, 10))

        # Кнопки
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Войти", command=self.login).pack(
            side=tk.RIGHT,
            padx=5
        )
        ttk.Button(btn_frame, text="Выход", command=self.cancel).pack(
            side=tk.RIGHT,
            padx=5
        )

        # Подсказка
        ttk.Label(main, text="Обратитесь к администратору для получения учётных данных",
                  foreground="gray", font=('Arial', 8)).pack(pady=(10, 0))

        # Привязываем Enter
        self.dialog.bind('<Return>', lambda e: self.login())

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Ошибка", "Введите логин и пароль")
            return

        # Аутентификация
        user = authenticate(username=username, password=password)

        if user and user.is_active:
            # Получаем расширенного пользователя из core.models
            try:
                self.user = User.objects.get(username=username)
                self.dialog.destroy()
            except User.DoesNotExist:
                messagebox.showerror("Ошибка", "Пользователь не найден")
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")

    def cancel(self):
        self.dialog.destroy()

    def run(self):
        self.dialog.wait_window()
        return self.user
