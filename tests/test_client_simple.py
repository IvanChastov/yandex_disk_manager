import pytest
from unittest.mock import Mock, patch
from core.yandex.client import YandexDiskClient


class TestYandexDiskClient:
    """Тесты клиента Яндекс.Диска (с моками, без БД)"""
    
    @patch('core.yandex.client.get_current_user')
    @patch('core.yandex.client.get_token_for_user')
    @patch('core.yandex.client.yadisk.Client')
    def test_client_initialization(self, mock_client_class, mock_get_token, mock_get_user):
        """Тест инициализации клиента"""
        mock_get_user.return_value = 'testuser'
        mock_get_token.return_value = 'fake_token_123'
        
        client = YandexDiskClient(username='testuser')
        assert client.username == 'testuser'
        assert client.token == 'fake_token_123'
    
    @patch('core.yandex.client.get_current_user')
    @patch('core.yandex.client.get_token_for_user')
    @patch('core.yandex.client.yadisk.Client')
    def test_get_files_list(self, mock_client_class, mock_get_token, mock_get_user):
        """Тест получения списка файлов"""
        mock_get_user.return_value = 'testuser'
        mock_get_token.return_value = 'fake_token_123'
        
        mock_client = Mock()
        mock_client.listdir.return_value = []
        mock_client_class.return_value = mock_client
        
        client = YandexDiskClient(username='testuser')
        client.client = mock_client
        result = client.get_files_list('/')
        assert result == []
    
    @patch('core.yandex.client.get_current_user')
    @patch('core.yandex.client.get_token_for_user')
    @patch('core.yandex.client.yadisk.Client')
    def test_upload_file(self, mock_client_class, mock_get_token, mock_get_user):
        """Тест загрузки файла"""
        mock_get_user.return_value = 'testuser'
        mock_get_token.return_value = 'fake_token_123'
        
        mock_client = Mock()
        mock_client.upload.return_value = True
        mock_client_class.return_value = mock_client
        
        client = YandexDiskClient(username='testuser')
        client.client = mock_client
        result = client.upload_file('/local/path.txt', '/remote/path.txt')
        assert result == True
    
    @patch('core.yandex.client.get_current_user')
    @patch('core.yandex.client.get_token_for_user')
    @patch('core.yandex.client.yadisk.Client')
    def test_download_file(self, mock_client_class, mock_get_token, mock_get_user):
        """Тест скачивания файла"""
        mock_get_user.return_value = 'testuser'
        mock_get_token.return_value = 'fake_token_123'
        
        mock_client = Mock()
        mock_client.download.return_value = True
        mock_client_class.return_value = mock_client
        
        client = YandexDiskClient(username='testuser')
        client.client = mock_client
        result = client.download_file('/remote/path.txt', '/local/path.txt')
        assert result == True
