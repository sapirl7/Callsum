# Architecture

Callsum состоит из двух runtime-компонентов:

1. `telegram_bot/bot.py`
Принимает Telegram webhook-и через AWS Lambda, пишет аудио в S3-compatible storage, создает запись задачи в DynamoDB и запускает RunPod endpoint.

2. `runpod_service/handler.py`
Работает как RunPod Serverless worker. Скачивает аудио по presigned URL, делает Whisper transcription, Pyannote diarization, Llama summarization и загружает результат обратно в storage.

Основной data flow:

1. Пользователь отправляет audio/voice в Telegram.
2. Telegram webhook приходит в API Gateway -> Lambda.
3. Lambda сохраняет аудио в S3/DO Spaces и отправляет job в RunPod.
4. RunPod worker обрабатывает аудио и сохраняет JSON результат.
5. Lambda получает подписанный callback от RunPod или пользователь забирает результат через `/status`.
