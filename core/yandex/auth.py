import webbrowser
import yadisk
import os

from django.conf import settings
from dotenv import load_dotenv


# Загружаем переменные окружения из .env файла
load_dotenv()

# Функции для получения ключей из переменных окружения
def get_client_id():
    """Получает Client ID из переменной окружения"""
    return os.getenv('YANDEX_CLIENT_ID')

def get_client_secret():
    """Получает Client Secret из переменной окружения"""
    return os.getenv('YANDEX_CLIENT_SECRET')

# URL для перенаправления
REDIRECT_URL = 'https://oauth.yandex.ru/verification_code'


def get_auth_url():
    """
    Генерирует URL для авторизации в Яндексе
    Пользователь должен перейти по этой ссылке и получить код
    """
    CLIENT_ID = get_client_id()
    CLIENT_SECRET = get_client_secret()

    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("Ключи приложения не найдены в .env файле")

    # Создаем временный клиент для получения URL
    client = yadisk.Client(CLIENT_ID, CLIENT_SECRET)

    # Получаем URL для авторизации
    auth_url = client.get_auth_url(
        type='code',
        redirect_uri=REDIRECT_URL,
        scope=[
            "cloud_api:disk.read",      # Чтение всего Диска
            "cloud_api:disk.write",     # Запись в любом месте
            "cloud_api:disk.info"       # Информация о Диске
        ]
    )

    return auth_url


def get_token_by_code(code):
    """
    Обменивает код подтверждения на токен доступа
    Args:
        code (str): Код подтверждения, полученный от Яндекса
    Returns:
        str: Токен доступа или None в случае ошибки
    """
    try:
        CLIENT_ID = get_client_id()
        CLIENT_SECRET = get_client_secret()

        if not CLIENT_ID or not CLIENT_SECRET:
            print("Ошибка: Ключи приложения не найдены")
            return None

        client = yadisk.Client(CLIENT_ID, CLIENT_SECRET)

        # Получаем токен по коду
        response = client.get_token(code, redirect_uri=REDIRECT_URL)

        # В ответе содержится access_token
        token = response.access_token

        return token
    except Exception as e:
        print(f"Ошибка получения токена: {e}")
        return None


def get_token_by_code_detailed(code):
    """
    Расширенная версия с возвратом всей информации о токене
    """
    try:
        CLIENT_ID = get_client_id()
        CLIENT_SECRET = get_client_secret()

        print(f"DEBUG: CLIENT_ID: {CLIENT_ID[:5]}...{CLIENT_ID[-5:]}")
        print(f"DEBUG: CLIENT_SECRET: {CLIENT_SECRET[:3]}...{CLIENT_SECRET[-3:]}")
        print(f"DEBUG: CODE: {code[:10]}...")

        if not CLIENT_ID or not CLIENT_SECRET:
            return {
                'success': False,
                'error': 'Ключи приложения не найдены в .env файле'
            }

        client = yadisk.Client(CLIENT_ID, CLIENT_SECRET)

        # Добавим отладочный вывод перед запросом
        print("DEBUG: Отправка запроса на получение токена...")

        response = client.get_token(code, redirect_uri=REDIRECT_URL)

        print(f"DEBUG: Ответ получен. Тип ответа: {type(response)}")
        print(f"DEBUG: Атрибуты ответа: {dir(response)}")

        # response содержит:
        # - access_token - сам токен
        # - token_type - тип токена (обычно "bearer")
        # - expires_in - через сколько секунд истечёт
        # - refresh_token - токен для обновления (если есть)

        return {
            'access_token': response.access_token,
            'token_type': response.token_type,
            'expires_in': response.expires_in,
            'refresh_token': getattr(response, 'refresh_token', None),
            'success': True
        }
    except Exception as e:
        print(f"DEBUG: Исключение: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def test_token(token):
    """
    Проверяет, работает ли токен
    Args:
        token (str): Токен для проверки
    Returns:
        bool: True если токен работает, False если нет
    """
    try:
        # Для проверки токена не нужны CLIENT_ID и CLIENT_SECRET
        client = yadisk.Client(token=token)

        # Пробуем получить информацию о диске
        info = client.get_disk_info()

        # Если дошли до сюда - токен работает
        print(f"Токен работает! Диск: {info.total_space / 1024**3:.1f} ГБ")
        return True
    except Exception as e:
        print(f"Токен не работает: {e}")
        return False
