FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY telegram_bot/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY telegram_bot /app/telegram_bot

WORKDIR /app/telegram_bot

CMD ["python", "bot_local.py"]
