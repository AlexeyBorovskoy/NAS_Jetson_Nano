# AI/ML-стек / AI/ML stack

**Дата / Date:** 2026-08-30.

## Вывод / Verdict: **NOT APPLICABLE — подтверждено предметно / confirmed with evidence, not a silent skip**

🇷🇺 NAS_Jetson_Nano — проект домашнего облака (фото/файлы/чат), не computer-vision или робототехническая платформа. Разделы про TensorRT-engine, CV pipeline и AI/ML-модели закрываются как неприменимые — с доказательствами ниже, а не пропуском.

🇬🇧 NAS_Jetson_Nano is a home-cloud project (photos/files/chat), not a computer-vision or robotics platform. The TensorRT-engine, CV-pipeline and AI/ML-model sections close as not applicable — with evidence below, not a silent skip.

## Доказательства / Evidence

1. **Модели проекта**: поиск `*.onnx`/`*.engine`/`*.trt` по всей ФС устройства (`find / -xdev`). Найдены только штатные демо-файлы JetPack SDK — `/usr/src/tensorrt/data/{mnist,resnet50,safe_plugin}/*.onnx`, `/usr/src/jetson_multimedia_api/data/Model/resnet10/*.onnx`. Это заводские примеры, ни один сервис проекта на них не ссылается.
2. **Код проекта**: `grep -ril 'rtsp\|gstreamer\|deepstream\|tensorrt\|onnx'` по `~/nasa` (Python/YAML/shell) → **ноль совпадений**.
3. **GStreamer**: `gst-launch-1.0` присутствует (штатно для JetPack), но `deepstream-app` **отсутствует**.
4. **Immich machine learning** (единственный сервис, который в принципе мог бы использовать ML — распознавание лиц/smart search): `docker-compose.immich.yml` — `IMMICH_DISABLE_MACHINE_LEARNING: ${IMMICH_DISABLE_MACHINE_LEARNING:-true}` (строки 61, 92) — **выключено по умолчанию**, отдельного контейнера `immich-machine-learning` в `docker ps` **нет**. Осознанное решение — 4 ГБ RAM Jetson не тянет.
5. **LLM Gateway**: inference выполняется **вне Jetson** — внешние API (DeepSeek, GigaChat) и Ollama на удалённой рабочей станции Vostro через обратный SSH-туннель (`172.17.0.1:11435`). Локального инференса на Jetson нет.
6. **Камеры/RTSP**: не обнаружено ни одного источника видео в проекте.

## NVIDIA software stack — установлен, но фактически не используется / installed but unused

| Компонент | Версия | Использование проектом |
|---|---|---|
| L4T / JetPack | R32.7.1 / JetPack 4.6.1 | база ОС, не выбор проекта |
| CUDA | 10.2.460 | 0 сервисов ссылается |
| cuDNN | 8.2.1.32 (по csv-манифесту) | 0 сервисов ссылается |
| TensorRT | 8.2.1.8 | 0 сервисов ссылается |
| NVIDIA Container Runtime | установлен (`nvidia-container-toolkit 1.7.0-1`), но `Default Runtime: runc` | 0 из 8 compose-файлов содержит `runtime: nvidia`/`NVIDIA_VISIBLE_DEVICES` (проверено `grep -rn` по всему `docker/compose/`) |

**Подтверждение простоя GPU / GPU idle confirmed**: `tegrastats` (15 замеров за 15 с) → `GR3D_FREQ = 0%` на всех точках. GPU физически простаивает всё время наблюдения.

## Интерпретация / Interpretation

🇷🇺 На Jetson установлен полноценный GPU/CUDA/TensorRT-стек (часть образа JetPack), но ни один сервис проекта его не задействует. Это не дефект — осознанный архитектурный выбор (4 ГБ RAM не оставляют запаса на ML-инференс рядом с Immich/Nextcloud/Postgres), но означает: если в будущем понадобится локальный CV/AI на Jetson — стек технически готов (JetPack 4.6.1 — потолок для Jetson Nano, новее не ставится), но текущая нагрузка (RAM, см. `RUNTIME.md`) не оставляет для него места без вытеснения существующих сервисов.

🇬🇧 A full GPU/CUDA/TensorRT stack is installed on the Jetson (part of the JetPack image), but no project service uses it. Not a defect — a deliberate architectural choice (4 GB RAM leaves no headroom for ML inference alongside Immich/Nextcloud/Postgres) — but it means: if local CV/AI on the Jetson is wanted later, the stack is technically ready (JetPack 4.6.1 is the ceiling for Jetson Nano, nothing newer installs), yet current RAM pressure leaves no room without displacing existing services.
