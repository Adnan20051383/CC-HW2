FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATA_DIR=/data

WORKDIR /app

COPY app/ ./app/

EXPOSE 8000

CMD ["python", "-m", "app.server"]