# Техническая документация

## Модели данных

### User
| Поле | Тип |
|------|-----|
| username | CharField |
| role | CharField (admin/manager/viewer) |
| yandex_token | TextField |

### Tag
| Поле | Тип |
|------|-----|
| name | CharField (уникальный) |
| color | CharField (HEX) |

### File
| Поле | Тип |
|------|-----|
| yandex_id | CharField (уникальный) |
| name | CharField |
| path | TextField |
| tags | ManyToManyField(Tag) |

### ChangeLog
| Поле | Тип |
|------|-----|
| change_type | CharField (created/modified/deleted) |
| source | CharField (app/direct) |
| changed_at | DateTimeField |

## Права доступа

| Роль | Просмотр | Загрузка | Удаление | Теги |
|------|----------|----------|----------|------|
| Admin | ✅ | ✅ | ✅ | ✅ |
| Manager | ✅ | ✅ | ❌ | ✅ |
| Viewer | ✅ | ❌ | ❌ | ❌ |

## Ограничения API

- Яндекс.Диск не даёт доступ к расшаренным папкам через чужой токен
- Мониторинг работает через опрос (polling), не в реальном времени