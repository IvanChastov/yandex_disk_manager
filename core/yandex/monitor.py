import time
import threading
from datetime import datetime, timedelta
from django.utils import timezone

from core.models import File, ChangeLog
from core.yandex.client import YandexDiskClient
from core.yandex.storage import get_current_user


class DiskMonitor:
    """
    Мониторинг изменений на Яндекс.Диске
    Запускается в фоновом потоке и периодически проверяет обновления
    """

    def __init__(self, username=None, check_interval=300):
        """
        Инициализация монитора

        Args:
            username (str): Имя пользователя, чей диск мониторим
            check_interval (int): Интервал проверки в секундах
        """
        self.username = username or get_current_user()
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.client = None

        if not self.username:
            raise ValueError("Не указан пользователь для мониторинга")

    def start(self):
        """Запускает мониторинг в фоновом потоке"""
        if self.running:
            print("Мониторинг уже запущен")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print(f"Мониторинг запущен для пользователя {self.username}")

    def stop(self):
        """Останавливает мониторинг"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("Мониторинг остановлен")

    def _run(self):
        """Основной цикл мониторинга (запускается в потоке)"""
        # Создаём клиент один раз при старте
        try:
            self.client = YandexDiskClient(username=self.username)
            print("Клиент Яндекс.Диска создан для мониторинга")
        except Exception as e:
            print(f"Ошибка создания клиента: {e}")
            self.running = False
            return

        while self.running:
            try:
                self._check_changes()
            except Exception as e:
                print(f"Ошибка при проверке изменений: {e}")

            # Ждём до следующей проверки
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _check_changes(self):
        """Проверяет изменения на диске"""
        print(f"\n Проверка изменений в {datetime.now().strftime('%H:%M:%S')}")

        # Получаем список всех файлов на диске (рекурсивно)
        all_files = self._get_all_files('/')

        # Получаем все файлы из БД
        db_files = {f.yandex_id: f for f in File.objects.all()}

        # Проверяем новые и изменённые файлы
        for file_info in all_files:
            if file_info.resource_id in db_files:
                # Файл есть в БД - проверяем, изменился ли
                self._check_modified_file(
                    file_info, db_files[file_info.resource_id]
                    )
                # Удаляем из словаря, чтобы потом найти удалённые
                del db_files[file_info.resource_id]
            else:
                # Новый файл
                self._handle_new_file(file_info)

        # Оставшиеся в db_files файлы - удалённые
        for yandex_id, db_file in db_files.items():
            self._handle_deleted_file(db_file)

    def _get_all_files(self, path, max_depth=10, current_depth=0):
        """
        Рекурсивно получает все файлы и папки

        Args:
            path (str): Путь для сканирования
            max_depth (int): Максимальная глубина рекурсии
            current_depth (int): Текущая глубина

        Returns:
            list: Список всех файлов и папок
        """
        if current_depth > max_depth:
            return []

        items = []
        try:
            files = self.client.get_files_list(path)
            for item in files:
                items.append(item)
                if item.type == 'dir' and current_depth < max_depth:
                    items.extend(self._get_all_files(
                        item.path, max_depth, current_depth + 1
                    ))
        except Exception as e:
            print(f"Ошибка получения списка {path}: {e}")

        return items

    def _check_modified_file(self, file_info, db_file):
        """Проверяет, изменился ли файл"""
        # Сравниваем дату модификации
        api_modified = file_info.modified.replace(tzinfo=timezone.utc)

        if api_modified > db_file.modified_at:
            # Проверяем, не было ли недавнего изменения от приложения
            recent_app_change = ChangeLog.objects.filter(
                file=db_file,
                source='app',
                changed_at__gte=timezone.now() - timedelta(seconds=30)
            ).exists()

            if recent_app_change:
                print(f"Пропускаем {file_info.name}"
                      f"(недавнее изменение от приложения)"
                      )
                # Всё равно обновляем дату в БД, чтобы не проверять снова
                db_file.modified_at = api_modified
                db_file.save()
                return

            print(f"Файл изменён напрямую: {file_info.name}")

            # Получаем mime_type
            mime_type = getattr(file_info, 'mime_type', None)
            if mime_type is None:
                mime_type = ''

            # Получаем size
            size = getattr(file_info, 'size', 0)
            if size is None:
                size = 0

            # Обновляем информацию в БД
            db_file.name = file_info.name
            db_file.path = file_info.path
            db_file.modified_at = api_modified
            db_file.size = size
            db_file.mime_type = mime_type
            db_file.save()

            # Создаём запись в логе (source='direct')
            ChangeLog.objects.create(
                file=db_file,
                file_path=file_info.path,
                change_type='modified',
                source='direct',
                changed_at=api_modified
            )

    def _handle_new_file(self, file_info):
        """Обрабатывает новый файл"""
        # Проверяем, не было ли недавнего создания от приложения
        recent_app_change = ChangeLog.objects.filter(
            file_path=file_info.path,
            source='app',
            change_type='created',
            changed_at__gte=timezone.now() - timedelta(seconds=30)
        ).exists()

        if recent_app_change:
            print(f"Пропускаем {file_info.name}"
                  f"(недавнее создание от приложения)"
                  )
            return

        print(f"Новый файл (напрямую): {file_info.name}")

        # Получаем mime_type
        mime_type = getattr(file_info, 'mime_type', None)
        if mime_type is None:
            mime_type = ''

        # Получаем size
        size = getattr(file_info, 'size', 0)
        if size is None:
            size = 0

        # Создаём запись в БД
        file_obj = File.objects.create(
            yandex_id=file_info.resource_id,
            name=file_info.name,
            path=file_info.path,
            type='file' if file_info.type == 'file' else 'dir',
            mime_type=mime_type,
            size=size,
            created_at=file_info.created,
            modified_at=file_info.modified,
        )

        # Создаём запись в логе (source='direct')
        ChangeLog.objects.create(
            file=file_obj,
            file_path=file_info.path,
            change_type='created',
            source='direct',
            changed_at=file_info.modified
        )

    def _handle_deleted_file(self, db_file):
        """Обрабатывает удалённый файл"""
        # Проверяем, не было ли недавнего удаления от приложения
        recent_app_change = ChangeLog.objects.filter(
            file=db_file,
            source='app',
            change_type='deleted',
            changed_at__gte=timezone.now() - timedelta(seconds=30)
        ).exists()

        if recent_app_change:
            print(f"Пропускаем удаление {db_file.name}"
                  f"(недавнее удаление от приложения)"
                  )
            db_file.delete()
            return

        print(f"Файл удалён напрямую: {db_file.name}")

        # Создаём запись в логе (source='direct')
        ChangeLog.objects.create(
            file=db_file,
            file_path=db_file.path,
            change_type='deleted',
            source='direct',
            changed_at=timezone.now()
        )

        # Удаляем файл из БД
        db_file.delete()


# Для тестирования
if __name__ == "__main__":
    # Запускаем мониторинг на 1 минуту с интервалом 10 секунд
    monitor = DiskMonitor(check_interval=10)
    monitor.start()

    try:
        time.sleep(60)  # Работаем 1 минуту
    finally:
        monitor.stop()
