FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app /app/app
# C8 (аудит 2026-09-19): не от root — шлюз ходит в интернет и принимает запросы из LAN/VPN.
# Том /data (учёт расходов, картинки) при выкате передаётся этому UID (runbook этапа C).
RUN useradd --system --uid 10001 --no-create-home gateway \n    && mkdir -p /data/images && chown -R 10001:10001 /data
USER 10001
EXPOSE 8090
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
