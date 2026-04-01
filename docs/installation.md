# Установка

## Для пользователя

1. Скачайте `YandexDiskManager.exe`
2. Запустите файл
3. Если антивирус блокирует — добавьте в исключения



## Для разработчика

### Требования
- Python 3.10+
- Git

### Клонирование и запуск

```bash
git clone https://github.com/ваш_логин/yandex-disk-manager.git
cd yandex-disk-manager
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python gui/app.py

Получение ключей Яндекс.OAuth
1. Перейдите на https://oauth.yandex.ru/

2. Создайте приложение

3. Укажите Redirect URI: https://oauth.yandex.ru/verification_code

4. Выберите права: cloud_api:disk.read, cloud_api:disk.write, cloud_api:disk.info

5. Скопируйте Client ID и Client Secret в файл .env