import os
import sys
import django

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.yandex.client import YandexDiskClient
from core.yandex.storage import get_current_user


def main():
    """Тестирование клиента Яндекс.Диска"""

    print("=" * 50)
    print("Тестирование клиента Яндекс.Диска")
    print("=" * 50)

    # Получаем текущего пользователя
    username = get_current_user()
    if not username:
        print("Пользователь не найден")
        return

    print(f"Текущий пользователь: {username}")

    try:
        # Создаём клиент
        client = YandexDiskClient(username=username)
        print("Клиент создан")

        # Получаем список файлов в корне
        print("\n Содержимое корневой папки:")
        files = client.get_files_list('/')

        print(f"DEBUG: Тип files: {type(files)}")
        print(f"DEBUG: Значение files: {files}")
        print(f"DEBUG: Длина files: {len(files) if files else 0}")

        if files is None:
            print("  Ошибка получения списка файлов (files is None)")
        elif len(files) == 0:
            print("  Папка пуста (files is empty)")
        else:
            print(f"  Получено {len(files)} элементов")
            for i, item in enumerate(files[:10]):  # Показываем первые 10
                file_type = "📁" if item.type == "dir" else "📄"
                size = getattr(item, 'size', 0)
                if size is None:
                    size = 0
                size_str = f"{size / 1024:.1f} КБ" if size > 0 else ""
                print(f"  {file_type} {item.name} {size_str}")

            if len(files) > 10:
                print(f"  ... и ещё {len(files) - 10} файлов")

        print("\n" + "=" * 50)
        print("Пытаемся получить информацию о диске...")
        print("=" * 50)

        # Получаем информацию о диске
        try:
            print("DEBUG: Вызов client.client.get_disk_info()...")
            info = client.client.get_disk_info()
            print(f"DEBUG: get_disk_info() выполнен, результат: {info}")
            print(f"DEBUG: Тип info: {type(info)}")

            if info:
                print(f"DEBUG: Атрибуты info: {dir(info)}")

                # Проверяем наличие атрибутов
                if hasattr(info, 'total_space'):
                    total = info.total_space / (1024**3)
                    print(f"DEBUG: total_space = {info.total_space}, total = {total}")
                else:
                    print("DEBUG: Нет атрибута total_space")

                if hasattr(info, 'used_space'):
                    used = info.used_space / (1024**3)
                    print(f"DEBUG: used_space = {info.used_space}, used = {used}")
                else:
                    print("DEBUG: Нет атрибута used_space")

                # Вычисляем свободное место
                if hasattr(info, 'total_space') and hasattr(info, 'used_space'):
                    total = info.total_space / (1024**3)
                    used = info.used_space / (1024**3)
                    free = total - used

                    print(f"\n Информация о диске:")
                    print(f"  Всего: {total:.1f} ГБ")
                    print(f"  Занято: {used:.1f} ГБ")
                    print(f"  Свободно: {free:.1f} ГБ")
                else:
                    print(" Недостаточно атрибутов для вычисления")
            else:
                print(" Информация о диске не получена (info is None)")

        except Exception as e:
            print(f" Исключение при получении информации о диске: {e}")
            print(f" Тип исключения: {type(e).__name__}")
            import traceback
            traceback.print_exc()

        print("\n" + "=" * 50)
        print("Тест завершён")
        print("=" * 50)

    except Exception as e:
        print(f" Ошибка в основном блоке: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
