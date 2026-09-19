# D3: задача внешнего сторожа для Cloud.ru Container Jobs (amd64).
FROM python:3.12-alpine
RUN apk add --no-cache openssh-client && adduser -D -u 10001 watch
COPY watchdog_job.py /app/watchdog_job.py
USER 10001
CMD ["python", "/app/watchdog_job.py"]
