import pytest
import os
import sys
import django

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Tag, File, ChangeLog

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Создаёт тестового пользователя"""
    user = User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='test@example.com'
    )
    user.role = 'viewer'
    user.save()
    return user


@pytest.fixture
def admin_user(db):
    """Создаёт администратора"""
    user = User.objects.create_user(
        username='admin',
        password='adminpass123',
        email='admin@example.com'
    )
    user.role = 'admin'
    user.is_superuser = True
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def manager_user(db):
    """Создаёт менеджера"""
    user = User.objects.create_user(
        username='manager',
        password='managerpass123',
        email='manager@example.com'
    )
    user.role = 'manager'
    user.save()
    return user


@pytest.fixture
def viewer_user(db):
    """Создаёт наблюдателя"""
    user = User.objects.create_user(
        username='viewer',
        password='viewerpass123',
        email='viewer@example.com'
    )
    user.role = 'viewer'
    user.save()
    return user


@pytest.fixture
def test_tag(db, test_user):
    """Создаёт тестовый тег"""
    tag = Tag.objects.create(
        name='Тестовый тег',
        color='#ff0000',
        created_by_id=test_user.id  # используем created_by_id вместо created_by
    )
    return tag


@pytest.fixture
def test_file(db):
    """Создаёт тестовый файл в БД"""
    file_obj = File.objects.create(
        yandex_id='test_123456',
        name='test_file.txt',
        path='disk:/test_file.txt',
        type='file',
        mime_type='text/plain',
        size=1024,
        created_at='2024-01-01T00:00:00Z',
        modified_at='2024-01-01T00:00:00Z'
    )
    return file_obj
