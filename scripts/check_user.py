import os
import sys
import django

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import User
from core.yandex.storage import get_current_user


def check_users():
    """Проверяет наличие пользователей в БД"""

    print("=" * 50)
    print("Проверка пользователей в БД")
    print("=" * 50)

    # Все пользователи
    users = User.objects.all()
    print(f"Всего пользователей: {users.count()}")

    for user in users:
        print(f"  - {user.username} (admin: {user.is_superuser}, active: {user.is_active})")

    # Текущий пользователь
    current = get_current_user()
    if current:
        print(f"\n Текущий пользователь: {current}")
    else:
        print("\n Текущий пользователь не найден")


if __name__ == "__main__":
    check_users()
