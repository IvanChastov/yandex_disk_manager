import tkinter as tk
from tkinter import ttk, messagebox

import webbrowser
import sys
import os


# Добавляем путь к проекту, чтобы импортировать модули
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настраиваем Django до импорта моделей
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.yandex.auth import get_auth_url, get_token_by_code_detailed, test_token
from core.yandex.storage import save_token_to_user, get_current_user


class AuthDialog:
    """
    Диалог авторизации в Яндекс.Диске
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.token = None

        # Создаём окно
        self.dialog = tk.Toplevel(parent) if parent else tk.Tk()
        self.dialog.title("Авторизация в Яндекс.Диске")
        self.dialog.geometry("700x650")
        self.dialog.resizable(False, False)

        # Центрируем окно
        self.center_window()

        # Создаём интерфейс
        self.create_widgets()

        # Если это главное окно, то закрытие приложения при закрытии окна
        if not parent:
            self.dialog.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self):
        """Центрирует окно на экране"""
        self.dialog.update_idletasks()

        # Получаем размеры окна
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()

        # Получаем размеры экрана
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()

        # Вычисляем координаты для центрирования
        # Используем целочисленное деление, чтобы получить целые числа
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

        # Убеждаемся, что координаты - целые числа
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        """Создаёт элементы интерфейса"""

        # Заголовок
        title = ttk.Label(
            self.dialog,
            text="Авторизация в Яндекс.Диске",
            font=('Arial', 14, 'bold')
        )
        title.pack(pady=20)

        # Инструкция
        instructions = """
    Для работы с Яндекс.Диском необходимо разрешить доступ.

    Шаг 1: Нажмите кнопку "Получить код" - откроется страница Яндекса
    Шаг 2: Войдите в свой аккаунт и разрешите доступ
    Шаг 3: Скопируйте полученный код и вставьте его в поле ниже
    """

        label = ttk.Label(self.dialog, text=instructions, justify=tk.LEFT)
        label.pack(pady=10, padx=20)

        # Кнопка для открытия ссылки
        self.auth_button = ttk.Button(
            self.dialog,
            text="1. Получить код",
            command=self.open_auth_url
        )
        self.auth_button.pack(pady=10)

        # Поле для ввода кода
        code_frame = ttk.Frame(self.dialog)
        code_frame.pack(pady=10, padx=20, fill=tk.X)

        ttk.Label(code_frame, text="Код подтверждения:").pack(anchor=tk.W)

        self.code_entry = tk.Text(code_frame, height=3, width=50, wrap=tk.WORD)
        self.code_entry.pack(fill=tk.X, pady=5)

        # Добавляем скроллбар для текстового поля
        scrollbar = ttk.Scrollbar(code_frame, orient=tk.VERTICAL, command=self.code_entry.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.code_entry.config(yscrollcommand=scrollbar.set)

        # Кнопка для вставки из буфера обмена
        paste_button = ttk.Button(
            code_frame,
            text="📋 Вставить из буфера",
            command=self.paste_from_clipboard
        )
        paste_button.pack(pady=5)

        # Привязываем события изменения текста (ТОЛЬКО ОДИН РАЗ!)
        self.code_entry.bind('<KeyRelease>', self.on_code_changed)
        self.code_entry.bind('<<Paste>>', self.on_code_changed)

        # Кнопка для получения токена
        self.token_button = ttk.Button(
            self.dialog, 
            text="2. Получить токен", 
            command=self.get_token,
            state=tk.DISABLED  # Изначально неактивна
        )
        self.token_button.pack(pady=5)

        # Статус
        self.status_var = tk.StringVar()
        self.status_var.set("Ожидание ввода кода...")
        self.status_label = ttk.Label(
            self.dialog,
            textvariable=self.status_var,
            foreground="gray"
        )
        self.status_label.pack(pady=10)

        # Кнопка закрытия
        self.close_button = ttk.Button(
            self.dialog,
            text="Закрыть",
            command=self.on_closing
        )
        self.close_button.pack(pady=10)

    def paste_from_clipboard(self):
        """Вставляет текст из буфера обмена"""
        try:
            clipboard_text = self.dialog.clipboard_get()
            self.code_entry.delete(1.0, tk.END)
            self.code_entry.insert(1.0, clipboard_text.strip())
            self.on_code_changed()
        except tk.TclError:
            messagebox.showwarning("Предупреждение", "Буфер обмена пуст или содержит не текст")

    def on_code_changed(self, event=None):
        """Активирует кнопку получения токена, если поле не пустое"""
        code = self.code_entry.get(1.0, tk.END).strip()
        if code:
            self.token_button.config(state=tk.NORMAL)
        else:
            self.token_button.config(state=tk.DISABLED)

    def open_auth_url(self):
        """Открывает URL авторизации в браузере"""
        try:
            auth_url = get_auth_url()
            webbrowser.open(auth_url)
            self.status_var.set(
                "Страница открыта в браузере. Войдите и скопируйте код.")
            self.status_label.config(foreground="green")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть страницу: {e}")
            self.status_var.set(f"Ошибка: {e}")
            self.status_label.config(foreground="red")

    def get_token(self):
        """Получает токен по коду"""
        code = self.code_entry.get(1.0, tk.END).strip()

        if not code:
            messagebox.showwarning(
                "Предупреждение", "Введите код подтверждения")
            return

        self.status_var.set("Получение токена...")
        self.status_label.config(foreground="blue")
        self.dialog.update()

        # Получаем токен
        result = get_token_by_code_detailed(code)

        # Проверяем структуру ответа
        if isinstance(result, dict) and result.get('success', False):
            self.token = result.get('access_token')

            if self.token:
                # Проверяем, работает ли токен
                self.status_var.set("Проверка токена...")
                self.dialog.update()

                if test_token(self.token):
                    self.status_var.set("Токен получен и работает!")
                    self.status_label.config(foreground="green")

                    # Показываем информацию о токене
                    expires = result.get('expires_in', 'неизвестно')
                    token_type = result.get('token_type', 'unknown')

                    messagebox.showinfo("Успех",
                        f"Токен успешно получен!\n\n"
                        f"Тип токена: {token_type}\n"
                        f"Срок действия: {expires} секунд\n\n"
                        f"Токен: {self.token[:20]}...\n\n"
                        f"Теперь можно работать с диском.")

                    # Сохраняем токен в базу данных
                    current_user = get_current_user()
                    if current_user:
                        if save_token_to_user(current_user, self.token):
                            self.status_var.set("Токен сохранён в базе данных")
                        else:
                            self.status_var.set("Токен получен, но не сохранён")
                    else:
                        self.status_var.set("Пользователь не найден, токен не сохранён")

                    # Закрываем диалог
                    self.dialog.after(1000, self.on_success)
                else:
                    self.status_var.set("Токен получен, но не работает")
                    self.status_label.config(foreground="red")
            else:
                self.status_var.set("Не удалось получить токен (пустой ответ)")
                self.status_label.config(foreground="red")
        else:
            error_msg = result.get('error', 'Неизвестная ошибка') if isinstance(result, dict) else str(result)
            self.status_var.set(f"Ошибка: {error_msg}")
            self.status_label.config(foreground="red")
            messagebox.showerror("Ошибка", f"Не удалось получить токен:\n{error_msg}")

    def on_success(self):
        """Вызывается при успешном получении токена"""
        self.dialog.destroy()

    def on_closing(self):
        """Закрытие окна"""
        if hasattr(self, 'token') and self.token:
            self.dialog.destroy()
        else:
            if messagebox.askyesno("Подтверждение", "Вы не получили токен. Выйти?"):
                self.dialog.destroy()

    def get_token_value(self):
        """Возвращает полученный токен"""
        return self.token

    def run(self):
        """Запускает диалог и возвращает токен после закрытия"""
        self.dialog.mainloop()
        return self.token


# Для тестирования диалога при запуске файла напрямую
if __name__ == "__main__":
    app = AuthDialog()
    token = app.run()
    if token:
        print(f"Получен токен: {token[:10]}...")
    else:
        print("Токен не получен")
