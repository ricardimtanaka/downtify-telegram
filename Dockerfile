FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir \
    python-telegram-bot==22.5 \
    httpx==0.28.1

COPY bot.py .

CMD ["python", "bot.py"]
