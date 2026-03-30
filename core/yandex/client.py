import yadisk
from datetime import datetime

from .storage import get_token_for_user, get_current_user
from core.models import File


class YandexDiskClient:
    """
    Клиент для работы с Яндекс.Диском
    """

    def __init__(self, token=None, username=None):
        """
        Инициализация клиента

        Args:
            token (str, optional): Токен доступа.
            Если не указан, берётся токен пользователя

            username (str, optional): Имя пользователя.
            Eсли не указано, берётся текущий
        """
        self.username = username or get_current_user()
        self.token = token or self._get_token_for_user()

        if not self.token:
            raise ValueError("Не удалось получить токен для пользователя")

        self.client = yadisk.Client(token=self.token)

    def _get_token_for_user(self):
        """Получает токен из БД для текущего пользователя"""
        if self.username:
            return get_token_for_user(self.username)
        return None

    def get_files_list(self, path='/'):
        """
        Получает список файлов и папок по указанному пути

        Args:
            path (str): Путь на диске (по умолчанию корень)
        Returns:
            list: Список файлов и папок
        """
        try:
            print(f"DEBUG: Запрос списка файлов для пути: {path}")
            items = list(self.client.listdir(path))
            print(f"DEBUG: Получено {len(items)} элементов")
            return items
        except Exception as e:
            print(f"Ошибка получения списка файлов: {e}")
            return None

    def get_file_info(self, path):
        """
        Получает информацию о конкретном файле/папке

        Args:
            path (str): Путь к фаайлу
        Returns:
            dict: Информация о файле, или None
        """
        try:
            return self.client.get_meta(path)
        except Exception as e:
            print(f"Ошибка получения информации о файле: {e}")
            return None

    def download_file(self, remote_path, local_path):
        """
        Скачивает файл с диска

        Args:
            remote_path (str): Путь к файлу на диске
            local_path (str): Путь для сохранения файла на локальном компьютере
        Returns:
            bool: True если успешно, False если ошибка
        """
        try:
            self.client.download(remote_path, local_path)
            print(f"Файл скачан: {remote_path} -> {local_path}")
            return True
        except Exception as e:
            print(f"Ошибка скачивания файла: {e}")
            return False

    def upload_file(self, local_path, remote_path):
        """Загружает файл на диск"""
        try:
            self.client.upload(local_path, remote_path)
            print(f"✅ Файл загружен: {local_path} -> {remote_path}")
            
            # Получаем информацию о загруженном файле и записываем изменение
            file_info = self.get_file_info(remote_path)
            if file_info:
                file_obj = self.sync_file_to_db(file_info)
                if file_obj:
                    self.record_change(file_obj, 'created')
                    print("DEBUG: Изменение записано в БД (upload)")
            
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            return False

    def create_folder(self, path):
        """
        Создаёт папку на диске
        """
        try:
            self.client.mkdir(path)
            print(f"Папка создана: {path}")

            # Получаем информацию о созданной папке и записываем изменение
            file_info = self.get_file_info(path)
            if file_info:
                file_obj = self.sync_file_to_db(file_info)
                if file_obj:
                    self.record_change(file_obj, 'created')

            return True
        except Exception as e:
            print(f"Ошибка создания папки: {e}")
            return False

    def delete_file(self, path):
        """Удаляет файл или папку"""
        try:
            # Сначала получаем информацию о файле
            file_info = self.get_file_info(path)
            if file_info:
                from core.models import File, ChangeLog
                
                try:
                    file_obj = File.objects.get(yandex_id=file_info.resource_id)
                    
                    # Записываем изменение
                    self.record_change(file_obj, 'deleted', old_path=path)
                    print(f"DEBUG: Запись deleted создана для {file_obj.name}")
                    
                    # Проверяем, что запись действительно создалась
                    last_change = ChangeLog.objects.filter(
                        file=file_obj,
                        change_type='deleted'
                    ).order_by('-changed_at').first()
                    
                    if last_change:
                        print(f"DEBUG: Подтверждение - запись deleted в БД (id={last_change.id})")
                    else:
                        print("DEBUG: ВНИМАНИЕ! Запись deleted НЕ найдена в БД!")
                    
                    # Удаляем файл из БД
                    file_obj.delete()
                    
                except File.DoesNotExist:
                    print(f"DEBUG: Файл не найден в БД для удаления: {path}")
            
            # Удаляем файл с диска
            self.client.remove(path)
            print(f"Удалено: {path}")
            return True
            
        except Exception as e:
            print(f"Ошибка удаления: {e}")
            return False

    def sync_file_to_db(self, file_info):
        """
        синхронизирует информацию о файле с базой данных

        Args:
            file_info: Объект файла из API Яндекса
        Returns:
            File: Объект модели File
        """
        try:
            file_obj, created = File.objects.update_or_create(
                yandex_id=file_info.resource_id,
                defaults={
                    'name': file_info.name,
                    'path': file_info.path,
                    'type': 'file' if file_info.type == 'file' else 'dir',
                    'mime_type': getattr(file_info, 'mime_type', ''),
                    'size': getattr(file_info, 'size', 0),
                    'created_at': file_info.created,
                    'modified_at': file_info.modified,
                }
            )
            if created:
                print(f"Добавлен новый файл в БД: {file_info.name}")
            else:
                print(f"Обновлен файл в БД: {file_info.name}")
            return file_obj
        except Exception as e:
            print(f"Ошибка синхронизации файла {file_info.name}: {e}")
            return None

    def record_change(self, file_obj, change_type, old_path=''):
        """Записывает изменение, сделанное через наше приложение"""
        from core.models import ChangeLog, User
        from django.utils import timezone
        
        try:
            user = User.objects.get(username=self.username)
        except User.DoesNotExist:
            user = None
        
        log = ChangeLog.objects.create(
            file=file_obj,
            file_path=file_obj.path,
            change_type=change_type,
            source='app',
            changed_by=user,
            changed_at=timezone.now(),
            old_path=old_path
        )
        print(f"DEBUG: Записано изменение в ChangeLog (id={log.id}, type={change_type}) для {file_obj.name}")
        return log.id
