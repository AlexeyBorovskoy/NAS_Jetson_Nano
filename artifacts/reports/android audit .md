Ты работаешь как инженерный аудитор проекта, Android automation reviewer, DevOps-reviewer и technical writer.

Проект: `NAS_Jetson_Nano` / `NAS_Jetson_Nano`

Идея проекта:

```text
Old Hardware Must Live — домашняя облачная платформа на базе Jetson Nano первого поколения, старого HDD, Docker/Nextcloud и Android-клиента.
```

Контекст:

В проекте уже есть общий audit report по серверной части, документации, Docker Compose, безопасности и open-source readiness.
Теперь нужен отдельный дополнительный аудит всего, что касается Android-телефона.

Пользователь сообщает, что Codex/агент сам настраивает Android-телефон, устанавливает необходимое ПО и готовит телефон к работе с домашним облаком.

Цель аудита:

1. Понять, что именно в проекте связано с Android.
2. Проверить, насколько воспроизводима автоматическая настройка телефона.
3. Проверить, какие приложения устанавливаются.
4. Проверить, какие команды ADB используются.
5. Проверить безопасность сценария.
6. Подготовить материал для будущей статьи о проекте.
7. Сформировать отдельный audit report по Android-контурy.

ВАЖНО:

На первом этапе работай в режиме read-only.
Не удаляй приложения.
Не сбрасывай телефон.
Не меняй настройки телефона без отдельного явного подтверждения.
Не устанавливай APK без подтверждения.
Не выводи в отчёт персональные данные, токены, пароли, номера телефонов, IMEI, serial number полностью, аккаунты Google, Wi-Fi пароли и другие секреты.

---

# 1. Аудит репозитория: Android-контур

Сначала изучи текущий репозиторий и найди всё, что связано с Android.

Проверь:

* README.md;
* docs/;
* scripts/;
* config/;
* tools/;
* mobile/;
* android/;
* adb/;
* phone/;
* client/;
* CLAUDE.md;
* AGENTS.md;
* Makefile;
* docker-compose файлы;
* install/deploy scripts.

Найди упоминания:

```text
Android
ADB
phone
mobile
Nextcloud client
Syncthing
DAVx5
WebDAV
Termux
KDE Connect
F-Droid
Aurora Store
Obsidian
KeePass
OpenVPN
WireGuard
Amnezia
Tailscale
ZeroTier
Immich
photo sync
contacts sync
calendar sync
file sync
```

Сформируй таблицу:

| Файл | Что найдено | Назначение | Комментарий |
| ---- | ----------- | ---------- | ----------- |

---

# 2. Проверка Android-сценария в документации

Оцени, есть ли в проекте понятная инструкция:

1. Как подготовить Android-телефон.
2. Как включить Developer Options.
3. Как включить USB Debugging.
4. Как подключить телефон к компьютеру.
5. Как проверить `adb devices`.
6. Какие приложения нужны.
7. Откуда приложения ставятся.
8. Какие разрешения нужны приложениям.
9. Как подключиться к Nextcloud.
10. Как настроить синхронизацию фото.
11. Как настроить синхронизацию файлов.
12. Как настроить контакты/календарь, если это предусмотрено.
13. Как проверить, что всё работает.
14. Как откатить изменения.
15. Какие риски безопасности есть.

Сделай оценку:

| Раздел | Есть/нет | Качество 1–10 | Что улучшить |
| ------ | -------- | ------------: | ------------ |

---

# 3. Проверка ADB-инструментов

Если в проекте есть скрипты, использующие ADB, проверь их.

Для каждого скрипта укажи:

| Скрипт | Что делает | Безопасность | Риски | Что исправить |
| ------ | ---------- | ------------ | ----- | ------------- |

Особо проверь наличие опасных команд:

```bash
adb shell pm uninstall
adb shell pm clear
adb shell settings put
adb shell appops set
adb reboot
adb reboot bootloader
adb sideload
adb install -r
adb push
adb pull
fastboot
factory reset
wipe
```

Если такие команды есть, классифицируй риск:

| Команда | Риск | Почему опасно | Как сделать безопаснее |
| ------- | ---- | ------------- | ---------------------- |

---

# 4. Если телефон подключён по ADB

Если телефон реально подключён и пользователь разрешил ADB, можно выполнить только безопасные read-only команды.

Сначала выполни:

```bash
adb devices
```

Если устройство найдено и статус `device`, выполни безопасные команды:

```bash
adb shell getprop ro.product.manufacturer
adb shell getprop ro.product.model
adb shell getprop ro.build.version.release
adb shell getprop ro.build.version.sdk
adb shell getprop ro.product.cpu.abi
adb shell getprop ro.build.fingerprint
adb shell settings get global adb_enabled
adb shell pm list packages
```

В отчёте НЕ выводи полный fingerprint, serial, IMEI, аккаунты, номера телефонов или личные данные.

Разрешено выводить обобщённо:

```text
Manufacturer: ...
Model: ...
Android version: ...
SDK: ...
CPU ABI: ...
ADB: enabled
Installed relevant packages: ...
```

Нельзя выполнять:

```bash
adb shell content query ...
adb pull /sdcard/...
adb backup
adb shell dumpsys account
adb shell dumpsys wifi
adb shell service call iphonesubinfo
```

Если телефон не подключён — не считай это ошибкой. Просто укажи, что аудит выполнен по репозиторию, без live-device проверки.

---

# 5. Аудит устанавливаемого ПО

Определи, какие приложения проект предполагает установить на Android.

Составь таблицу:

| Приложение | Назначение | Источник установки | Нужно ли для MVP | Риски |
| ---------- | ---------- | ------------------ | ---------------- | ----- |

Проверь возможные категории:

## 5.1. Nextcloud

* Nextcloud Android client;
* авто-загрузка фото;
* синхронизация файлов;
* работа с сервером в локальной сети;
* работа через HTTPS/VPN;
* настройки автозагрузки;
* battery optimization exclusions.

## 5.2. Фото и медиа

* Immich;
* Nextcloud auto upload;
* DCIM sync;
* screenshots sync;
* ограничения мобильного интернета.

## 5.3. Контакты и календарь

* DAVx5;
* CalDAV;
* CardDAV;
* синхронизация контактов;
* синхронизация календаря;
* риски дублирования контактов.

## 5.4. Файлы и заметки

* Syncthing;
* Obsidian;
* Markor;
* Nextcloud Notes;
* WebDAV client.

## 5.5. Безопасный доступ

* WireGuard;
* OpenVPN;
* Amnezia;
* Tailscale;
* ZeroTier;
* HTTPS reverse proxy.

## 5.6. Служебные инструменты

* Termux;
* F-Droid;
* Aurora Store;
* KDE Connect;
* SSH client.

---

# 6. Проверка воспроизводимости Android-настройки

Оцени, можно ли другому пользователю повторить Android-настройку по проекту.

Проверь:

1. Есть ли список совместимых Android-версий.
2. Есть ли список проверенных моделей телефонов.
3. Есть ли инструкция по включению USB debugging.
4. Есть ли инструкция по ADB на Windows/Linux.
5. Есть ли список устанавливаемых APK/пакетов.
6. Есть ли ссылки на официальные магазины или F-Droid.
7. Есть ли настройка разрешений.
8. Есть ли настройка автозапуска/фоновой работы.
9. Есть ли проверка синхронизации.
10. Есть ли rollback-инструкция.
11. Есть ли troubleshooting.
12. Есть ли предупреждения о приватности.

Сделай оценку reproducibility от 1 до 10.

---

# 7. Проверка безопасности Android-настройки

Оцени риски:

* включённый USB debugging;
* установка APK из неизвестных источников;
* хранение паролей Nextcloud;
* хранение app passwords;
* токены в скриптах;
* передача файлов по HTTP;
* отсутствие HTTPS;
* работа через публичный IP;
* VPN;
* потеря телефона;
* доступ к фото и контактам;
* синхронизация личных данных;
* конфликт с Google backup;
* battery optimization;
* MDM/рабочий профиль;
* приватность метаданных фото.

Составь таблицу:

| Риск | Вероятность | Последствия | Как снизить |
| ---- | ----------- | ----------- | ----------- |

---

# 8. Что обязательно надо отразить в статье

На основе аудита сформируй раздел для будущей статьи:

```markdown
## Android-клиент как часть домашнего облака
```

В этом разделе должны быть тезисы:

1. Зачем вообще нужен Android в проекте.
2. Почему телефон — не просто клиент, а часть экосистемы.
3. Какие задачи решает телефон:

   * фото в домашнее облако;
   * доступ к файлам;
   * просмотр документов;
   * синхронизация заметок;
   * контакты/календарь, если используется;
   * доступ через VPN/HTTPS.
4. Что автоматизирует Codex/агент.
5. Что всё равно надо делать руками.
6. Какие риски безопасности.
7. Что получилось.
8. Что ещё не автоматизировано.

---

# 9. Что добавить в репозиторий после аудита

Сформируй список рекомендуемых файлов:

```text
docs/20_android_overview.md
docs/21_android_adb_setup.md
docs/22_android_apps.md
docs/23_android_nextcloud_client.md
docs/24_android_photo_sync.md
docs/25_android_contacts_calendar.md
docs/26_android_security.md
docs/27_android_troubleshooting.md
scripts/android_check_adb.sh
scripts/android_list_relevant_apps.sh
scripts/android_install_apps_plan.sh
config/android_apps.example.yml
```

Для каждого файла опиши:

| Файл | Зачем нужен | Что должен содержать |
| ---- | ----------- | -------------------- |

---

# 10. Итоговый отчёт

Сформируй итоговый отчёт в Markdown:

```markdown
# Android Audit Report: NAS_Jetson_Nano

## 1. Executive summary
## 2. What Android role exists in the project
## 3. Repository findings
## 4. ADB automation findings
## 5. Android apps and services
## 6. Reproducibility assessment
## 7. Security assessment
## 8. Data privacy risks
## 9. What should be added to docs
## 10. What should be added to scripts
## 11. Article material: Android client section
## 12. Priority action plan
```

---

# 11. Оценки

Поставь оценки:

| Категория             | Оценка 1–10 | Комментарий |
| --------------------- | ----------: | ----------- |
| Android documentation |             |             |
| ADB automation safety |             |             |
| Reproducibility       |             |             |
| Security              |             |             |
| User friendliness     |             |             |
| Article readiness     |             |             |

---

# 12. Приоритетный план

В конце дай план:

## CRITICAL

Что нужно сделать перед публикацией статьи.

## HIGH

Что нужно сделать для воспроизводимости.

## MEDIUM

Что можно сделать после MVP.

## LOW

Что можно оставить на будущее.

---

# 13. Ограничения

Не меняй телефон без подтверждения.
Не устанавливай APK без подтверждения.
Не удаляй приложения.
Не очищай данные приложений.
Не выполняй factory reset.
Не выводи секреты и персональные данные.
Не делай root.
Не разблокируй bootloader.
Не сохраняй личные данные телефона в репозиторий.
Не публикуй скриншоты телефона с личной информацией.

Начни с read-only аудита репозитория и, если доступен телефон по ADB, только с безопасной диагностики.
