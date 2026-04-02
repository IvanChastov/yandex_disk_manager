from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    """Расширенная модель пользователя с ролями"""

    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('viewer', 'Наблюдатель'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='viewer',
        verbose_name='Роль'
    )

    # Токен доступа к Яндекс.Диску (будет зашифрован позже)
    yandex_token = models.TextField(
        blank=True,
        verbose_name='Токен Яндекс.Диска'
    )

    # Дата последней синхронизации с диском
    last_sync = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Последняя синхронизация'
    )

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='core_user_set',  # Уникальное имя для обратной связи
        related_query_name='core_user',
    )

    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='core_user_set',  # Уникальное имя для обратной связи
        related_query_name='core_user',
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'


class Tag(models.Model):
    """Тег для маркировки файлов"""

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Название'
    )

    color = models.CharField(
        max_length=7,
        default='#3498db',
        verbose_name='Цвет (HEX)'
    )

    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Создатель'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    def __str__(self):
        return f"{self.name} ({self.color})"

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']


class File(models.Model):
    """Информация о файле на Яндекс.Диске"""

    FILE_TYPES = [
        ('file', 'Файл'),
        ('dir', 'Папка'),
    ]

    # Уникальный идентификатор файла на Яндекс.Диске (Никогда не меняется)
    yandex_id = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='ID на Яндекс.Диске'
    )

    name = models.CharField(
        max_length=255,
        verbose_name='Имя файла'
    )

    path = models.TextField(
        verbose_name='Путь к файлу на диске'
    )

    type = models.CharField(
        max_length=50,
        choices=FILE_TYPES,
        verbose_name='Тип'
    )

    mime_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='MIME-тип'
    )

    size = models.BigIntegerField(
        default=0,
        blank=True,
        null=True,
        verbose_name='Размер (байт)'
    )

    created_at = models.DateTimeField(
        verbose_name='Дата создания на диске'
    )

    modified_at = models.DateTimeField(
        verbose_name='Дата обновления на диске'
    )

    # Связь с тегами (многие ко многим)
    tags = models.ManyToManyField(
        Tag,
        related_name='files',
        blank=True,
        verbose_name='Теги'
    )

    # Кто создал/изменил (из пользователей приложения)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_files',
        verbose_name='Создал (пользователь)'
    )

    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_files',
        verbose_name='Изменил (пользователь)'
    )

    # Дата последней синхронизации с БД
    last_synced = models.DateTimeField(
        auto_now=True,
        verbose_name='Последняя синхронизация'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Файл'
        verbose_name_plural = 'Файлы'
        ordering = ['path']


class ChangeLog(models.Model):
    """Лог изменений файлов"""

    CHANGE_TYPES = [
        ('created', 'Создан'),
        ('modified', 'Изменён'),
        ('moved', 'Перемещен'),
        ('deleted', 'Удален'),
    ]

    SOURCE_TYPES = [
        ('app', 'Через приложение'),
        ('direct', 'Напрямую через диск'),
        ('unknown', 'Неизвестно'),
    ]

    file = models.ForeignKey(
        File,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Файл'
    )

    # Путь на момент изменения (на случай, если файл удален)
    file_path = models.TextField(
        verbose_name='Путь к файлу'
    )

    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPES,
        verbose_name='Тип изменения'
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_TYPES,
        default='app',
        verbose_name='Источник'
    )

    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Кто изменил'
    )

    changed_at = models.DateTimeField(
        verbose_name='Время изменения'
    )

    detected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время обнаружения'
    )

    old_path = models.TextField(
        blank=True,
        verbose_name='Старый путь (для перемещений)'
    )

    def __str__(self):
        return f"{self.get_change_type_display()}: {self.file_path}"

    class Meta:
        verbose_name = 'Запись изменений'
        verbose_name_plural = 'история изменений'
        ordering = ['-changed_at']
