import pytest
from core.permissions import has_permission
from core.models import User  # импортируем из core.models, а не из django.contrib.auth


@pytest.mark.django_db
class TestPermissions:
    """Тесты системы прав доступа"""
    
    def test_admin_has_all_permissions(self):
        admin = User.objects.create_user(username='admin', password='pass')
        admin.role = 'admin'
        admin.save()
        
        assert has_permission('admin', 'view') == True
        assert has_permission('admin', 'upload') == True
        assert has_permission('admin', 'delete') == True
        assert has_permission('admin', 'manage_tags') == True
        assert has_permission('admin', 'manage_users') == True
    
    def test_manager_permissions(self):
        manager = User.objects.create_user(username='manager', password='pass')
        manager.role = 'manager'
        manager.save()
        
        assert has_permission('manager', 'view') == True
        assert has_permission('manager', 'upload') == True
        assert has_permission('manager', 'manage_tags') == True
        assert has_permission('manager', 'delete') == False
        assert has_permission('manager', 'manage_users') == False
    
    def test_viewer_permissions(self):
        viewer = User.objects.create_user(username='viewer', password='pass')
        viewer.role = 'viewer'
        viewer.save()
        
        assert has_permission('viewer', 'view') == True
        assert has_permission('viewer', 'upload') == False
        assert has_permission('viewer', 'delete') == False
        assert has_permission('viewer', 'manage_tags') == False
    
    def test_nonexistent_user(self):
        assert has_permission('nonexistent', 'view') == False
