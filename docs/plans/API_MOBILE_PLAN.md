# План: NAS_Jetson_Nano API для мобильных приложений / NAS_Jetson_Nano API Plan for Mobile Apps

> 🇷🇺 План расширения nas_jetson_nano-api до единого фасада для семейных приложений.
> 🇬🇧 Plan to extend nas_jetson_nano-api into a unified facade for family apps.

## Текущее состояние / Current State

`nas_jetson_nano-api` уже работает на `192.168.0.50:8099` с Swagger UI (`/docs`).
Написан на FastAPI (Python). Покрывает: статус системы, healthcheck, диагностика.

## Концепция / Concept

```
Телефон / Browser
      │
      ▼
┌─────────────────────────────────┐
│      nas_jetson_nano-api  :8099            │  ← единая точка входа
│      FastAPI + Swagger          │  ← авторизация: один токен
└──────┬──────┬──────┬────────────┘
       │      │      │
       ▼      ▼      ▼
   Nextcloud Immich  System
   :8080    :2283   (docker, storage)
```

Мобильное приложение общается только с nas_jetson_nano-api — не с Nextcloud/Immich напрямую.
Один логин, один токен, один URL.

## Модули API / API Modules

### 1. Auth (`/api/auth`)
- `POST /api/auth/login` — логин, возвращает JWT токен
- `POST /api/auth/refresh` — обновление токена
- `GET  /api/auth/me` — текущий пользователь

### 2. System (`/api/system`) — уже частично есть
- `GET /api/system/status` — статус всех сервисов
- `GET /api/system/storage` — дисковое пространство
- `GET /api/system/containers` — статус Docker контейнеров

### 3. Photos (`/api/photos`) — проксирует Immich
- `GET  /api/photos` — список фото с пагинацией
- `GET  /api/photos/{id}` — одно фото
- `POST /api/photos/upload` — загрузка
- `GET  /api/photos/albums` — альбомы

### 4. Files (`/api/files`) — проксирует Nextcloud WebDAV
- `GET  /api/files` — список файлов
- `GET  /api/files/{path}` — скачать файл
- `POST /api/files/{path}` — загрузить файл
- `DELETE /api/files/{path}` — удалить

### 5. Contacts (`/api/contacts`) — проксирует Nextcloud CardDAV
- `GET  /api/contacts` — все контакты
- `POST /api/contacts` — создать контакт
- `PUT  /api/contacts/{id}` — обновить
- `DELETE /api/contacts/{id}` — удалить

### 6. Calendar (`/api/calendar`) — проксирует Nextcloud CalDAV
- `GET  /api/calendar/events` — события
- `POST /api/calendar/events` — создать событие

### 7. Notifications (`/api/notifications`)
- `POST /api/notifications/register` — регистрация push-токена
- События: SSD упал, бэкап выполнен, новое фото от члена семьи

## Swagger / OpenAPI

FastAPI генерирует Swagger автоматически:
- UI: `http://192.168.0.50:8099/docs`
- OpenAPI JSON: `http://192.168.0.50:8099/openapi.json`
- ReDoc: `http://192.168.0.50:8099/redoc`

По `openapi.json` можно автоматически генерировать клиентский код
для Android (Kotlin), iOS (Swift), Flutter, React Native.

## Мобильное приложение — стек / Mobile App Stack

**Рекомендуется: Flutter** (один код → Android + iOS)

```
flutter create nas_jetson_nano_family_app
# Генерация клиента из OpenAPI:
openapi-generator generate -i http://192.168.0.50:8099/openapi.json \
  -g dart -o lib/api_client
```

**Минимальный MVP приложения:**
1. Экран входа (логин / пароль → JWT)
2. Лента фото (через /api/photos)
3. Файлы (через /api/files)
4. Статус системы (через /api/system/status)

## Этапы реализации / Implementation Stages

| Этап | Описание | Оценка |
|---|---|---|
| 1 | Auth модуль (JWT) | 2-4 часа |
| 2 | System + Storage endpoints | 1-2 часа |
| 3 | Photos прокси (Immich) | 4-6 часов |
| 4 | Files прокси (Nextcloud WebDAV) | 4-6 часов |
| 5 | Contacts + Calendar прокси | 4-6 часов |
| 6 | Push-уведомления | 6-8 часов |
| 7 | Flutter MVP приложение | 16-24 часа |

## Безопасность / Security

- JWT токены с TTL 24ч, refresh токен 30 дней
- Все эндпоинты через HTTPS (уже есть :9443 на VPS)
- Rate limiting (уже есть в nginx)
- Логи запросов в /var/log/nas_jetson_nano-monitor/api-access.log
- Пароли никогда не проксируются — только токены

## Следующий шаг

Реализовать Auth модуль в `services/nas_jetson_nano-api/app/`:
- Добавить `/api/auth/login` с проверкой через Nextcloud LDAP/Basic Auth
- Возвращать JWT
- Добавить middleware `verify_token` на все защищённые эндпоинты
