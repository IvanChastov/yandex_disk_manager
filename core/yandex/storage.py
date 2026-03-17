from core.models import User


def save_token_to_user(username, token):
    """
    Сохраняет токен для указанного пользователя
    Args:
        username (str): Имя пользователя в системе
        token (str): Токен доступа к Яндекс.Диску
    Returns:
        bool: True, если успешно, False, если пользователь не найден
    """
    try:
        user = User.objects.get(username=username)
        user.yandex_token = token
        user.save()
        print(f"Токен сохранён для пользователя {username}")
        return True
    except User.DoesNotExist:
        print(f"Пользователь {username} не найден")
        return False


def get_token_for_user(username):
    """
    Получает токен для указанного пользователя
    Args:
        username (str): Имя пользователя в системе
    Returns:
        str: Токен или None, если не найден
    """
    try:
        user = User.objects.get(username=username)
        token = user.yandex_token
        if token:
            print(f"Токен найден для пользователя {username}")
            return token
        else:
            print(f"У пользователя {username} нет токена")
            return None
    except User.DoesNotExist:
        print(f"Пользователь {username} не найден")
        return None


def get_current_user():
    """
    Получает текущего пользователя.
    Пока берёт первого активного пользователя из БД.

    Returns:
        str: Имя пользователя или None
    """
    try:
        # Пробуем получить первого активного пользователя (не суперадмина)
        user = User.objects.filter(is_active=True).first()
        if user:
            print(f"Текущий пользователь: {user.username}")
            return user.username
        else:
            print("Нет активных пользователей в БД")
            return None
    except Exception as e:
        print(f"Ошибка получения пользователя: {e}")
        return None
