FROM python:3.12-slim
WORKDIR /app
COPY proxy.py /app/proxy.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 2375
CMD ["python", "/app/proxy.py"]
