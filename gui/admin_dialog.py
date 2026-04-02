import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import User


class AdminDialog:
    """Диалог администратора для управления пользователями"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Администрирование")
        self.dialog.geometry("800x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        self.load_users()
        self.center_window()
    
    def center_window(self):
        self.dialog.update_idletasks()
        w = self.dialog.winfo_width()
        h = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f'{w}x{h}+{x}+{y}')
    
    def create_widgets(self):
        main = ttk.Frame(self.dialog, padding="10")
        main.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        ttk.Label(main, text="Управление пользователями", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # Кнопки
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="Добавить", command=self.add_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Редактировать", command=self.edit_user).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self.delete_user).pack(side=tk.LEFT, padx=5)
        
        # Таблица
        columns = ('username', 'email', 'role', 'is_active')
        self.tree = ttk.Treeview(main, columns=columns, show='headings', height=15)
        
        self.tree.heading('username', text='Логин')
        self.tree.heading('email', text='Email')
        self.tree.heading('role', text='Роль')
        self.tree.heading('is_active', text='Активен')
        
        self.tree.column('username', width=150)
        self.tree.column('email', width=200)
        self.tree.column('role', width=100)
        self.tree.column('is_active', width=70)
        
        scrollbar = ttk.Scrollbar(main, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопка закрытия
        ttk.Button(main, text="Закрыть", command=self.dialog.destroy).pack(pady=10)
    
    def load_users(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for user in User.objects.all():
            role_display = dict(User.ROLE_CHOICES).get(user.role, user.role)
            self.tree.insert('', tk.END, values=(
                user.username,
                user.email or '',
                role_display,
                'Да' if user.is_active else 'Нет'
            ), tags=(user.id,))
    
    def add_user(self):
        dialog = UserEditDialog(self.dialog, None)
        if dialog.run():
            self.load_users()
            messagebox.showinfo("Успех", "Пользователь создан")
    
    def edit_user(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите пользователя")
            return
        
        user_id = self.tree.item(selection[0], 'tags')[0]
        user = User.objects.get(id=user_id)
        
        dialog = UserEditDialog(self.dialog, user)
        if dialog.run():
            self.load_users()
            messagebox.showinfo("Успех", "Пользователь обновлён")
    
    def delete_user(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите пользователя")
            return
        
        user_id = self.tree.item(selection[0], 'tags')[0]
        user = User.objects.get(id=user_id)
        
        if messagebox.askyesno("Подтверждение", f"Удалить пользователя '{user.username}'?"):
            user.delete()
            self.load_users()
    
    def run(self):
        self.dialog.wait_window()


class UserEditDialog:
    def __init__(self, parent, user=None):
        self.parent = parent
        self.user = user
        self.result = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Редактирование пользователя")
        self.dialog.geometry("350x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        self.load_user_data()
        self.center_window()
    
    def center_window(self):
        self.dialog.update_idletasks()
        w = self.dialog.winfo_width()
        h = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (w // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f'{w}x{h}+{x}+{y}')
    
    def create_widgets(self):
        main = ttk.Frame(self.dialog, padding="15")
        main.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main, text="Логин:").pack(anchor=tk.W)
        self.username_entry = ttk.Entry(main, width=30)
        self.username_entry.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(main, text="Email:").pack(anchor=tk.W)
        self.email_entry = ttk.Entry(main, width=30)
        self.email_entry.pack(fill=tk.X, pady=(0, 10))
        
        if not self.user:
            ttk.Label(main, text="Пароль:").pack(anchor=tk.W)
            self.password_entry = ttk.Entry(main, show="*", width=30)
            self.password_entry.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(main, text="Роль:").pack(anchor=tk.W)
        self.role_var = tk.StringVar()
        role_combo = ttk.Combobox(main, textvariable=self.role_var, values=['admin', 'manager', 'viewer'], state='readonly')
        role_combo.pack(fill=tk.X, pady=(0, 10))
        
        self.active_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main, text="Активен", variable=self.active_var).pack(anchor=tk.W, pady=5)
        
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=15)
        
        ttk.Button(btn_frame, text="Сохранить", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=self.cancel).pack(side=tk.RIGHT, padx=5)
    
    def load_user_data(self):
        if self.user:
            self.username_entry.insert(0, self.user.username)
            self.username_entry.config(state='readonly')
            self.email_entry.insert(0, self.user.email or '')
            self.role_var.set(self.user.role)
            self.active_var.set(self.user.is_active)
    
    def save(self):
        username = self.username_entry.get().strip()
        email = self.email_entry.get().strip()
        role = self.role_var.get()
        is_active = self.active_var.get()
        
        if not username:
            messagebox.showerror("Ошибка", "Логин обязателен")
            return
        
        if not role:
            messagebox.showerror("Ошибка", "Выберите роль")
            return
        
        if self.user:
            self.user.email = email
            self.user.role = role
            self.user.is_active = is_active
            self.user.save()
        else:
            password = self.password_entry.get()
            if not password:
                messagebox.showerror("Ошибка", "Пароль обязателен")
                return
            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                is_active=is_active
            )
        
        self.result = True
        self.dialog.destroy()
    
    def cancel(self):
        self.dialog.destroy()
    
    def run(self):
        self.dialog.wait_window()
        return self.result
