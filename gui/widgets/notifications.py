import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import threading
import time
import csv
from datetime import datetime, timedelta

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Настраиваем Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import ChangeLog


class NotificationsWidget(ttk.Frame):
    """Виджет для отображения уведомлений об изменениях"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.running = False
        self.thread = None
        self.notifications = []

        self.create_widgets()
        self.start_monitor()

    def create_widgets(self):
        """Создаёт элементы интерфейса"""
        # Заголовок с кнопкой экспорта
        title_frame = ttk.Frame(self)
        title_frame.pack(fill=tk.X, pady=5)

        ttk.Label(title_frame, text="История изменений", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        export_button = ttk.Button(
            title_frame,
            text="Экспорт в CSV",
            command=self.export_report,
            width=8
        )
        export_button.pack(side=tk.RIGHT, padx=5)
        
        # --- ПАНЕЛЬ ФИЛЬТРА ---
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Показать:").pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar(value="all")
        
        filter_periods = [
            ("всё", "all"),
            ("сегодня", "day"),
            ("неделя", "week"),
            ("месяц", "month")
        ]
        
        for text, value in filter_periods:
            rb = ttk.Radiobutton(
                filter_frame,
                text=text,
                value=value,
                variable=self.filter_var,
                command=self.refresh
            )
            rb.pack(side=tk.LEFT, padx=5)
        # --- КОНЕЦ ПАНЕЛИ ФИЛЬТРА ---
        
        # Treeview для отображения изменений
        columns = ('time', 'type', 'file', 'user', 'source')
        self.tree = ttk.Treeview(self, columns=columns, show='headings', height=12)
        
        self.tree.heading('time', text='Время')
        self.tree.heading('type', text='Тип')
        self.tree.heading('file', text='Файл')
        self.tree.heading('user', text='Пользователь')
        self.tree.heading('source', text='Источник')
        
        self.tree.column('time', width=120)
        self.tree.column('type', width=80)
        self.tree.column('file', width=250)
        self.tree.column('user', width=100)
        self.tree.column('source', width=80)
        
        # Скроллбар
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Размещение
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Настройка цветов для разных источников
        self.tree.tag_configure('app', background='#e8f5e8')
        self.tree.tag_configure('direct', background='#fff3e0')

    def start_monitor(self):
        """Запускает фоновый поток для проверки новых уведомлений"""
        self.running = True
        self.thread = threading.Thread(
            target=self._check_notifications, daemon=True
            )
        self.thread.start()

    def stop_monitor(self):
        """Останавливает фоновый поток"""
        self.running = False

    def _check_notifications(self):
        """Фоновый поток для проверки новых уведомлений"""
        last_check = datetime.now() - timedelta(minutes=5)

        while self.running:
            try:
                # Получаем новые изменения за последние 30 секунд
                new_changes = ChangeLog.objects.filter(
                    detected_at__gte=datetime.now() - timedelta(seconds=30)
                ).order_by('-changed_at')[:10]

                for change in new_changes:
                    if change.id not in self.notifications:
                        self.notifications.append(change.id)
                        # Обновляем UI в основном потоке
                        self.after(0, self._add_notification, change)

                time.sleep(5)  # Проверяем каждые 5 секунд
            except Exception as e:
                print(f"ошибка в мониторинге уведомлений: {e}")
                time.sleep(10)

    def _add_notification(self, change):
        """Добавляет уведомление в список (вызывается в основном потоке)"""
        # Форматируем время
        time_str = change.changed_at.strftime("%d.%m %H:%M")
        
        # Определяем тип изменения (без иконок)
        type_text = {
            'created': 'Создан',
            'modified': 'Изменён',
            'moved': 'Перемещён',
            'deleted': 'Удалён',
        }.get(change.change_type, change.change_type)
        
        # Определяем пользователя
        user_name = change.changed_by.username if change.changed_by else ""
        
        # Определяем источник
        source_text = {
            'app': 'из приложения',
            'direct': 'напрямую',
            'unknown': 'неизвестно',
        }.get(change.source, change.source)
        
        # Определяем цвет строки
        tag = 'app' if change.source == 'app' else 'direct'
        
        # Добавляем в Treeview
        self.tree.insert(
            '', 
            0, 
            values=(
                time_str,
                type_text,
                change.file_path.split('/')[-1] if change.file_path else '',
                user_name,
                source_text
            ),
            tags=(tag,)
        )
        
        # Если много записей, удаляем старые
        if len(self.tree.get_children()) > 100:
            self.tree.delete(self.tree.get_children()[-1])

    def refresh(self):
        """Обновляет список уведомлений из БД с учётом фильтра"""
        from core.models import ChangeLog
        from django.utils import timezone
        from datetime import timedelta
        
        print("DEBUG: refresh() вызван в notifications")
        
        # Очищаем список
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.notifications = []
        
        # Определяем фильтр по дате
        filter_value = self.filter_var.get()
        now = timezone.now()
        
        if filter_value == "day":
            start_date = now - timedelta(days=1)
        elif filter_value == "week":
            start_date = now - timedelta(days=7)
        elif filter_value == "month":
            start_date = now - timedelta(days=30)
        else:  # "all"
            start_date = None
        
        # Получаем изменения с учётом фильтра
        if start_date:
            recent = ChangeLog.objects.filter(
                changed_at__gte=start_date
            ).order_by('-changed_at')[:100]
        else:
            recent = ChangeLog.objects.all().order_by('-changed_at')[:100]
        
        print(f"DEBUG: Найдено изменений в БД: {recent.count()}")
        
        # Выводим все типы изменений
        for change in recent:
            file_name = change.file_path.split('/')[-1] if change.file_path else "Неизвестно"
            print(f"DEBUG: {change.change_type} - {file_name} (id={change.id})")
        
        for change in recent:
            self._add_notification(change)
            if change.id not in self.notifications:
                self.notifications.append(change.id)

    def export_report(self):
        """Экспортирует историю изменений в CSV файл"""
        from django.utils import timezone
        from datetime import timedelta
        
        # Спрашиваем у пользователя куда сохранить
        file_path = filedialog.asksaveasfilename(
            title="Сохранить отчёт",
            defaultextension=".csv",
            filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")]
        )
        
        if not file_path:
            return
        
        # Определяем фильтр по дате
        filter_value = self.filter_var.get()
        now = timezone.now()
        
        if filter_value == "day":
            start_date = now - timedelta(days=1)
        elif filter_value == "week":
            start_date = now - timedelta(days=7)
        elif filter_value == "month":
            start_date = now - timedelta(days=30)
        else:
            start_date = None
        
        # Получаем данные с учётом фильтра
        if start_date:
            changes = ChangeLog.objects.filter(
                changed_at__gte=start_date
            ).order_by('-changed_at')
        else:
            changes = ChangeLog.objects.all().order_by('-changed_at')
        
        # Записываем в CSV
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                # Заголовки
                writer.writerow([
                    'Дата и время',
                    'Тип изменения',
                    'Путь к файлу',
                    'Имя файла',
                    'Пользователь',
                    'Источник'
                ])
                
                # Данные
                for change in changes:
                    writer.writerow([
                        change.changed_at.strftime('%d.%m.%Y %H:%M'),
                        change.get_change_type_display(),
                        change.file_path,
                        change.file_path.split('/')[-1] if change.file_path else '',
                        change.changed_by.username if change.changed_by else '',
                        change.get_source_display()
                    ])
            
            messagebox.showinfo("Успех", f"Отчёт сохранён в:\n{file_path}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить отчёт:\n{e}")
