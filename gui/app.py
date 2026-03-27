"""
Точка входа в графическое приложение
"""

import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настраиваем Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from gui.main_window import MainWindow


def main():
    """Запускает приложение"""
    app = MainWindow()
    app.run()


if __name__ == "__main__":
    main()
