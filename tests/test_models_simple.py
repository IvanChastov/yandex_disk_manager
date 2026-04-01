import pytest
from django.utils import timezone
from core.models import Tag, File, ChangeLog


@pytest.mark.django_db
class TestTagModel:
    """Тесты модели Tag (простые)"""
    
    def test_tag_creation(self):
        tag = Tag.objects.create(name='Тестовый тег', color='#ff0000')
        assert tag.name == 'Тестовый тег'
        assert tag.color == '#ff0000'
    
    def test_tag_str(self):
        tag = Tag.objects.create(name='Тестовый тег', color='#ff0000')
        assert str(tag) == "Тестовый тег (#ff0000)"
    
    def test_unique_tag_name(self):
        Tag.objects.create(name='Уникальный тег', color='#ff0000')
        with pytest.raises(Exception):
            Tag.objects.create(name='Уникальный тег', color='#00ff00')


@pytest.mark.django_db
class TestFileModel:
    """Тесты модели File"""
    
    def test_file_creation(self):
        now = timezone.now()
        file_obj = File.objects.create(
            yandex_id='test_123',
            name='test.txt',
            path='disk:/test.txt',
            type='file',
            size=1024,
            created_at=now,
            modified_at=now
        )
        assert file_obj.name == 'test.txt'
        assert file_obj.size == 1024
    
    def test_file_str(self):
        now = timezone.now()
        file_obj = File.objects.create(
            yandex_id='test_123',
            name='test.txt',
            path='disk:/test.txt',
            type='file',
            created_at=now,
            modified_at=now
        )
        assert str(file_obj) == 'test.txt'


@pytest.mark.django_db
class TestChangeLogModel:
    """Тесты модели ChangeLog"""
    
    def test_changelog_creation(self):
        now = timezone.now()
        file_obj = File.objects.create(
            yandex_id='test_123',
            name='test.txt',
            path='disk:/test.txt',
            type='file',
            created_at=now,
            modified_at=now
        )
        log = ChangeLog.objects.create(
            file=file_obj,
            file_path=file_obj.path,
            change_type='created',
            source='app',
            changed_at=now
        )
        assert log.change_type == 'created'
        assert log.source == 'app'
    
    def test_changelog_ordering(self):
        now = timezone.now()
        file_obj = File.objects.create(
            yandex_id='test_123',
            name='test.txt',
            path='disk:/test.txt',
            type='file',
            created_at=now,
            modified_at=now
        )
        import time
        log1 = ChangeLog.objects.create(
            file=file_obj,
            file_path=file_obj.path,
            change_type='created',
            changed_at=now
        )
        time.sleep(0.1)
        log2 = ChangeLog.objects.create(
            file=file_obj,
            file_path=file_obj.path,
            change_type='modified',
            changed_at=timezone.now()
        )
        logs = ChangeLog.objects.all()
        assert logs[0] == log2
