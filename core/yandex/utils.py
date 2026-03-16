import os
from dotenv import load_dotenv

load_dotenv()


def check_credentials():
    """
    Проверяет наличие ключей в .env файле
    """
    client_id = os.getenv('YANDEX_CLIENT_ID')
    client_secret = os.getenv('YANDEX_CLIENT_SECRET')

    if not client_id:
        print("❌ YANDEX_CLIENT_ID не найден в .env файле")
    else:
        print(f"✅ YANDEX_CLIENT_ID: {client_id[:5]}...{client_id[-5:]}")

    if not client_secret:
        print("❌ YANDEX_CLIENT_SECRET не найден в .env файле")
    else:
        print(
            f"✅ YANDEX_CLIENT_SECRET: {client_secret[:3]}...{client_secret[-3:]}")

    return client_id and client_secret


if __name__ == "__main__":
    # Если файл запущен напрямую, проверяем ключи
    check_credentials()
