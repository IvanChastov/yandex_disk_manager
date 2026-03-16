from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Tag, File, ChangeLog


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Настройка отображения пользователей в админке"""

    # Поля, отображаемые в списке пользователей
    list_display = ('username', 'email', 'role', 'last_sync', 'is_active')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email')

    # Поля, которые можно редактировать в карточке пользователя
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительные поля', {
            'fields': ('role',),
        }),
    )

    # Поля, отображаемые при создании пользователя
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительные поля', {
            'fields': ('role',),
        }),
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Настройка отображения тегов"""

    list_display = ('name', 'color', 'created_by', 'created_at')
    list_filter = ('created_by',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    """Настройка отображения файлов"""

    list_display = ('name', 'type', 'size_display', 'modified_at', 'tag_list')
    list_filter = ('type', 'modified_at', 'tags')
    search_fields = ('name', 'path')
    readonly_fields = ('yandex_id', 'created_at', 'modified_at', 'last_synced')

    def size_display(self, obj):
        """Форматирование размера файла"""
        if obj.size < 1024:
            return f"{obj.size} Б"
        elif obj.size < 1024 * 1024:
            return f"{obj.size / 1024:.1f} КБ"
        elif obj.size < 1024 * 1024 * 1024:
            return f"{obj.size / (1024 * 1024):.1f} МБ"
        else:
            return f"{obj.size / (1024 * 1024 * 1024):.1f} ГБ"
    size_display.short_description = 'Размер'

    def tag_list(self, obj):
        """Отображение тегов в виде строки"""
        return ", ".join([tag.name for tag in obj.tags.all()])
    tag_list.short_description = 'Теги'


@admin.register(ChangeLog)
class ChangeLogAdmin(admin.ModelAdmin):
    """Настройка отображения лога и изменений"""

    list_display = ('changed_at', 'change_type',
                    'file_path', 'source', 'changed_by')
    list_filter = ('change_type', 'source', 'changed_at')
    search_fields = ('file_path', 'old_path')
    readonly_fields = ('detected_at',)

    def has_add_permission(self, request):
        """Запрещаем добавлять записи вручную"""
        return False

    def has_change_permission(self, request, obj=None):
        """Запрещаем изменять записи"""
        return False
