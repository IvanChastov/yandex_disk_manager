from core.models import User


def has_permission(username, action):
    """
    Проверяет, есть ли у пользователя право на действие

    Args:
        username (str): Имя пользователя
        action (str): Действие ('view', 'upload', 'delete', 'manage_tags', 'manage_users')

    Returns:
        bool: True если разрешено, False если нет
    """
    try:
        user = User.objects.get(username=username)
        role = user.role
    except User.DoesNotExist:
        return False

    permissions = {
        'viewer': ['view'],
        'manager': ['view', 'upload', 'manage_tags'],
        'admin': ['view', 'upload', 'delete', 'manage_tags', 'manage_users']
    }

    return action in permissions.get(role, [])
