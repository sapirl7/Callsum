# API Reference

Внешний API у проекта минимальный.

## Telegram webhook

- `POST /webhook`
- Источник: Telegram Bot API
- Защита: заголовок `X-Telegram-Bot-Api-Secret-Token`

## Health check

- `GET /health`
- Возвращает mock-response из API Gateway

## RunPod callback

- `POST /webhook`
- Источник: RunPod worker
- Защита: заголовок `X-Runpod-Callback-Token`

RunPod callback использует тот же endpoint Lambda, но определяется по наличию полей `job_id` и `status` в payload.
