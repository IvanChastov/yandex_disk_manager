import os
import sys
import django
import time

# Настраиваем Django (скрипт в корне, поэтому путь правильный)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.yandex.monitor import DiskMonitor
from core.yandex.storage import get_current_user
from core.models import ChangeLog


def main():
    """Тестирование мониторинга изменений"""

    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ФОНОВОГО МОНИТОРИНГА")
    print("=" * 60)

    # Получаем текущего пользователя
    username = get_current_user()
    if not username:
        print("Пользователь не найден")
        return

    print(f"Текущий пользователь: {username}")

    # Показываем последние записи в ChangeLog до запуска
    print("\n Последние изменения в БД (до запуска):")
    recent = ChangeLog.objects.all().order_by('-changed_at')[:5]
    if recent:
        for log in recent:
            print(f"{log.changed_at.strftime('%H:%M:%S')}"
                  f" - {log.change_type} - {log.file_path}"
                  )
    else:
        print("  История изменений пуста")

    # Запускаем мониторинг
    print("\n Запуск мониторинга (интервал 10 секунд)...")
    monitor = DiskMonitor(username=username, check_interval=10)
    monitor.start()

    print("\n Мониторинг работает 30 секунд...")
    print("В это время можете изменить файлы на диске через веб-интерфейс")
    print("Изменения будут отображаться ниже:\n")

    # Ждём 30 секунд, показывая обратный отсчёт
    for i in range(30, 0, -5):
        time.sleep(5)
        print(f"Осталось {i} секунд...")

        # Показываем новые изменения
        new_logs = ChangeLog.objects.all().order_by('-changed_at')[:3]
        if new_logs:
            print("Последние изменения:")
            for log in new_logs[:3]:
                source_icon = "🟢" if log.source == 'app' else "🟠"
                print(f"{source_icon} {log.changed_at.strftime('%H:%M:%S')}"
                      f" - {log.change_type} - {log.file_path}"
                      )

    # Останавливаем мониторинг
    monitor.stop()

    # Показываем итоговые изменения
    print("\n" + "=" * 60)
    print("ИТОГОВЫЕ ИЗМЕНЕНИЯ ЗА ВРЕМЯ ТЕСТА:")
    print("=" * 60)

    recent = ChangeLog.objects.all().order_by('-changed_at')[:10]
    if recent:
        for log in recent:
            source_icon = "🟢" if log.source == 'app' else "🟠"
            print(f"{source_icon} {log.changed_at.strftime('%H:%M:%S')}"
                  f"- {log.change_type} - {log.file_path}"
                  )
    else:
        print("Изменений не обнаружено")

    print("\n Тест завершён")


if __name__ == "__main__":
    main()
