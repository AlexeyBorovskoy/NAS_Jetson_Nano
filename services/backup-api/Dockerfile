FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app /app/app
# BK-2 (аудит 2026-09-26): не от root — как llm-gateway (C8).
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin backup
USER 10001
EXPOSE 8095
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8095"]
