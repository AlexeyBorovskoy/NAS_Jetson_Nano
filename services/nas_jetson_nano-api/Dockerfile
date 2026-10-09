FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements.lock /app/
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: -r /app/requirements.lock
COPY app /app/app
RUN groupadd --gid 10001 nasapi && useradd --uid 10001 --gid nasapi --no-create-home nasapi \
    && mkdir -p /var/log/nas_jetson_nano-monitor \
    && chown nasapi:nasapi /var/log/nas_jetson_nano-monitor
ENV PYTHONDONTWRITEBYTECODE=1
USER 10001:10001
EXPOSE 8099
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8099"]
