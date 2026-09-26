# homecloud_stt — Vosk small-ru для голосовых сообщений (E10). Собирается на Jetson (arm64).
# python:3.12-slim уже есть на устройстве. alphacephei.com и github.com с домашнего интернета
# Jetson недоступны (TLS-таймаут, замер 2026-09-20) — модель берётся с зеркала HuggingFace
# (тот же официальный zip) и сверяется по SHA-256, снятой на устройстве 2026-09-26.
FROM python:3.12-slim

ARG MODEL_URL=https://huggingface.co/localstack/vosk-models/resolve/main/vosk-model-small-ru-0.22.zip
ARG MODEL_SHA256=961d5ff98a17f4aa6de69864d0aa71fa5bac682301d2b5d17a3f24c5c99a46d4

RUN apt-get update \
 && apt-get install -y --no-install-recommends opus-tools curl unzip ca-certificates \
 && curl -fsSL -o /tmp/model.zip "$MODEL_URL" \
 && echo "$MODEL_SHA256  /tmp/model.zip" | sha256sum -c - \
 && unzip -q /tmp/model.zip -d /opt \
 && mv /opt/vosk-model-small-ru-0.22 /opt/model \
 && rm -f /tmp/model.zip \
 && apt-get purge -y curl unzip && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir vosk==0.3.45

COPY stt_server.py /app/stt_server.py
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin stt
USER 10001
WORKDIR /app
EXPOSE 8790
CMD ["python", "/app/stt_server.py"]
