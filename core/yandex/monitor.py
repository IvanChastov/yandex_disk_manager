import time
import threading
from datetime import datetime, timedelta
from django.utils import timezone

from core.models import File, ChangeLog
from core.yandex.client import YandexDiskClient
from core.yandex.storage import get_current_user


class DiskMonitor:
    def __init__(self, username=None, check_interval=300, on_change_callback=None, corporate_token=None):
        self.username = username
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.client = None
        self.on_change_callback = on_change_callback
        self.corporate_token = corporate_token  # Добавляем возможность передать токен напрямую

        # Если передан токен, не требуем username
        if not self.corporate_token and not self.username:
            self.username = get_current_user()
            if not self.username:
                raise ValueError("Не указан пользователь для мониторинга")

    def start(self):
        if self.running:
            print("Мониторинг уже запущен")
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print(f"Мониторинг запущен для пользователя {self.username or 'корпоративный'}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("Мониторинг остановлен")

    def _run(self):
        try:
            # Если есть корпоративный токен, используем его
            if self.corporate_token:
                self.client = YandexDiskClient(token=self.corporate_token)
            else:
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
            
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _check_changes(self):
        print(f"\n Проверка изменений в {datetime.now().strftime('%H:%M:%S')}")

        all_files = self._get_all_files('/')
        db_files = {f.yandex_id: f for f in File.objects.all()}
        changes_detected = False

        for file_info in all_files:
            if file_info.resource_id in db_files:
                if self._check_modified_file(file_info, db_files[file_info.resource_id]):
                    changes_detected = True
                del db_files[file_info.resource_id]
            else:
                self._handle_new_file(file_info)
                changes_detected = True

        for yandex_id, db_file in db_files.items():
            self._handle_deleted_file(db_file)
            changes_detected = True

        if changes_detected and self.on_change_callback:
            self.on_change_callback()

    def _get_all_files(self, path, max_depth=10, current_depth=0):
        if current_depth > max_depth:
            return []
        items = []
        try:
            files = self.client.get_files_list(path)
            for item in files:
                items.append(item)
                if item.type == 'dir' and current_depth < max_depth:
                    items.extend(self._get_all_files(item.path, max_depth, current_depth + 1))
        except Exception as e:
            print(f"Ошибка получения списка {path}: {e}")
        return items

    def _check_modified_file(self, file_info, db_file):
        api_modified = file_info.modified.replace(tzinfo=timezone.utc)

        if api_modified > db_file.modified_at:
            recent_app_change = ChangeLog.objects.filter(
                file=db_file,
                source='app',
                changed_at__gte=timezone.now() - timedelta(seconds=30)
            ).exists()

            if recent_app_change:
                print(f"Пропускаем {file_info.name} (недавнее изменение от приложения)")
                db_file.modified_at = api_modified
                db_file.save()
                return False

            print(f"Файл изменён напрямую: {file_info.name}")

            mime_type = getattr(file_info, 'mime_type', None) or ''
            size = getattr(file_info, 'size', 0) or 0

            db_file.name = file_info.name
            db_file.path = file_info.path
            db_file.modified_at = api_modified
            db_file.size = size
            db_file.mime_type = mime_type
            db_file.save()

            ChangeLog.objects.create(
                file=db_file,
                file_path=file_info.path,
                change_type='modified',
                source='direct',
                changed_at=api_modified
            )
            return True
        return False

    def _handle_new_file(self, file_info):
        recent_app_change = ChangeLog.objects.filter(
            file_path=file_info.path,
            source='app',
            change_type='created',
            changed_at__gte=timezone.now() - timedelta(seconds=30)
        ).exists()

        if recent_app_change:
            print(f"Пропускаем {file_info.name} (недавнее создание от приложения)")
            return

        print(f"Новый файл (напрямую): {file_info.name}")

        mime_type = getattr(file_info, 'mime_type', None) or ''
        size = getattr(file_info, 'size', 0) or 0

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

        ChangeLog.objects.create(
            file=file_obj,
            file_path=file_info.path,
            change_type='created',
            source='direct',
            changed_at=file_info.modified
        )

    def _handle_deleted_file(self, db_file):
        recent_app_change = ChangeLog.objects.filter(
            file=db_file,
            source='app',
            change_type='deleted',
            changed_at__gte=timezone.now() - timedelta(seconds=30)
        ).exists()

        if recent_app_change:
            print(f"Пропускаем удаление {db_file.name} (недавнее удаление от приложения)")
            db_file.delete()
            return

        print(f"Файл удалён напрямую: {db_file.name}")

        ChangeLog.objects.create(
            file=db_file,
            file_path=db_file.path,
            change_type='deleted',
            source='direct',
            changed_at=timezone.now()
        )
        db_file.delete()
