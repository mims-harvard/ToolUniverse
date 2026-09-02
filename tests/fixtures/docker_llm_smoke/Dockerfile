FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup -S app && adduser -S -G app -u 10001 app
WORKDIR /app
COPY server.py /app/server.py
USER app
EXPOSE 8000

CMD ["python", "/app/server.py"]
