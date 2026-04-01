import os
import sys
import django

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Проверяем, есть ли база данных
from django.db import connections
from django.db.utils import OperationalError

def init_database():
    """Создаёт таблицы, если их нет"""
    try:
        # Проверяем, есть ли таблица core_tag
        from core.models import Tag
        Tag.objects.exists()
        print("База данных уже инициализирована")
    except OperationalError:
        # Таблиц нет — выполняем миграции
        print("Создание базы данных...")
        from django.core.management import call_command
        call_command('migrate', interactive=False)
        print("База данных создана")

# Инициализируем базу
django.setup()
init_database()

# Запускаем приложение
from gui.app import main
main()
