# -*- coding: utf-8 -*-
"""
Telegram Bot for receiving voice messages and sending results.
Deployed as an AWS Lambda function.
"""

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import boto3
import httpx
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


logger = logging.getLogger()
logger.setLevel(logging.INFO)


SUPPORTED_AUDIO_FORMATS = {
    "audio/ogg",
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
}

DEFAULT_AWS_REGION = "us-east-1"
RUNPOD_CALLBACK_HEADER = "x-runpod-callback-token"

_runtime_services: Optional["RuntimeServices"] = None
_bot_instance: Optional[Bot] = None


@dataclass
class RuntimeServices:
    s3_client: Any
    jobs_table: Any
    rate_limits_table: Any
    s3_bucket: str
    runpod_endpoint: Optional[str]
    runpod_api_key: Optional[str]
    callback_url: Optional[str]
    telegram_secret_token: str
    runpod_callback_token: str
    max_audio_duration: int
    min_audio_duration: int
    max_file_size_mb: int
    free_tier_requests_per_hour: int
    free_tier_requests_per_day: int
    max_retries: int
    retry_backoff_multiplier: int
    retry_min_wait: int
    retry_max_wait: int
    telegram_max_message_length: int


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        logger.warning("Invalid integer for %s=%r, using default %s", name, value, default)
        return default


def get_aws_region() -> str:
    return os.getenv("AWS_REGION", DEFAULT_AWS_REGION)


def get_secret(secret_arn: Optional[str], key: Optional[str] = None, fallback_env_var: Optional[str] = None):
    """
    Retrieves a secret from AWS Secrets Manager.

    Falls back to an environment variable if secret_arn is not provided or the secret is unavailable.
    """
    if not secret_arn:
        return os.getenv(fallback_env_var) if fallback_env_var else None

    try:
        secrets_client = boto3.client("secretsmanager", region_name=get_aws_region())
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response["SecretString"])
        return secret if key is None else secret.get(key)
    except Exception as exc:
        logger.error("Error retrieving secret %s: %s", secret_arn, exc)
        return os.getenv(fallback_env_var) if fallback_env_var else None


def get_telegram_token() -> Optional[str]:
    telegram_secret_arn = os.getenv("TELEGRAM_BOT_TOKEN_SECRET_ARN")
    return get_secret(telegram_secret_arn, "token", "TELEGRAM_BOT_TOKEN")


def require_bot_token() -> str:
    token = get_telegram_token()
    if token:
        return token

    raise RuntimeError(
        "Telegram bot token is not configured. "
        "Set TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN_SECRET_ARN."
    )


def get_runpod_api_key() -> Optional[str]:
    runpod_secret_arn = os.getenv("RUNPOD_API_KEY_SECRET_ARN")
    return get_secret(runpod_secret_arn, "api_key", "RUNPOD_API_KEY")


def build_s3_client():
    s3_config = {
        "service_name": "s3",
        "region_name": get_aws_region(),
    }

    endpoint_url = os.getenv("S3_ENDPOINT_URL")
    if endpoint_url:
        s3_config["endpoint_url"] = endpoint_url

    do_spaces_arn = os.getenv("DO_SPACES_SECRET_ARN")
    do_spaces_secret = get_secret(do_spaces_arn)
    if isinstance(do_spaces_secret, dict):
        access_key = do_spaces_secret.get("access_key")
        secret_key = do_spaces_secret.get("secret_key")
        if access_key and secret_key:
            s3_config["aws_access_key_id"] = access_key
            s3_config["aws_secret_access_key"] = secret_key

    return boto3.client(**s3_config)


def get_runtime_services() -> RuntimeServices:
    global _runtime_services

    if _runtime_services is not None:
        return _runtime_services

    s3_client = build_s3_client()
    dynamodb = boto3.resource("dynamodb", region_name=get_aws_region())

    telegram_secret_token = os.getenv("TELEGRAM_SECRET_TOKEN", "")
    runpod_callback_token = os.getenv("RUNPOD_CALLBACK_TOKEN") or telegram_secret_token

    jobs_table_name = os.getenv("DYNAMODB_TABLE_NAME", "callsum-jobs")
    rate_limits_table_name = os.getenv("RATE_LIMITS_TABLE_NAME", f"{jobs_table_name}-rate-limits")

    _runtime_services = RuntimeServices(
        s3_client=s3_client,
        jobs_table=dynamodb.Table(jobs_table_name),
        rate_limits_table=dynamodb.Table(rate_limits_table_name),
        s3_bucket=os.getenv("S3_BUCKET_NAME", "callsum-prod"),
        runpod_endpoint=os.getenv("RUNPOD_ENDPOINT_URL"),
        runpod_api_key=get_runpod_api_key(),
        callback_url=os.getenv("CALLBACK_URL"),
        telegram_secret_token=telegram_secret_token,
        runpod_callback_token=runpod_callback_token,
        max_audio_duration=get_env_int("MAX_AUDIO_DURATION_SECONDS", 7200),
        min_audio_duration=get_env_int("MIN_AUDIO_DURATION_SECONDS", 1),
        max_file_size_mb=get_env_int("MAX_FILE_SIZE_MB", 100),
        free_tier_requests_per_hour=get_env_int("FREE_TIER_REQUESTS_PER_HOUR", 10),
        free_tier_requests_per_day=get_env_int("FREE_TIER_REQUESTS_PER_DAY", 50),
        max_retries=get_env_int("MAX_RETRIES", 3),
        retry_backoff_multiplier=get_env_int("RETRY_BACKOFF_MULTIPLIER", 2),
        retry_min_wait=get_env_int("RETRY_MIN_WAIT_SECONDS", 2),
        retry_max_wait=get_env_int("RETRY_MAX_WAIT_SECONDS", 10),
        telegram_max_message_length=get_env_int("TELEGRAM_MAX_MESSAGE_LENGTH", 4000),
    )
    return _runtime_services


def validate_processing_runtime() -> RuntimeServices:
    runtime = get_runtime_services()

    missing = []
    if not runtime.runpod_endpoint:
        missing.append("RUNPOD_ENDPOINT_URL")
    if not runtime.runpod_api_key:
        missing.append("RUNPOD_API_KEY / RUNPOD_API_KEY_SECRET_ARN")
    if runtime.callback_url and not runtime.runpod_callback_token:
        missing.append("RUNPOD_CALLBACK_TOKEN or TELEGRAM_SECRET_TOKEN")

    if missing:
        raise RuntimeError(
            "Processing runtime is not configured: missing " + ", ".join(missing)
        )

    return runtime


def get_bot() -> Bot:
    global _bot_instance

    if _bot_instance is None:
        _bot_instance = Bot(token=require_bot_token())

    return _bot_instance


def build_application() -> Application:
    application = Application.builder().token(require_bot_token()).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_handler))
    return application


def estimate_processing_time(duration_seconds: int) -> int:
    """
    Estimates audio processing time.

    1 hour of audio ≈ 20 minutes of processing on RTX 3090.
    """
    return max(1, int(duration_seconds / 60 * 0.33))


def check_rate_limit(user_id: int) -> dict:
    """
    Checks rate limit for a user.

    Returns:
        dict: {'allowed': bool, 'reset_in': int (seconds), 'message': str}
    """
    runtime = get_runtime_services()

    try:
        now = datetime.utcnow()
        current_hour = int(now.timestamp() // 3600) * 3600
        current_day = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

        try:
            hour_response = runtime.rate_limits_table.get_item(
                Key={"user_id": user_id, "window_start": current_hour}
            )
            hour_count = hour_response.get("Item", {}).get("count", 0)

            if hour_count >= runtime.free_tier_requests_per_hour:
                reset_in = 3600 - (int(now.timestamp()) - current_hour)
                return {
                    "allowed": False,
                    "reset_in": reset_in,
                    "message": (
                        "⏱ Превышен лимит запросов в час "
                        f"({runtime.free_tier_requests_per_hour}/час).\n"
                        f"Попробуйте через {reset_in // 60} мин."
                    ),
                }
        except Exception as exc:
            logger.warning("Error checking hourly limit: %s", exc)

        try:
            day_response = runtime.rate_limits_table.get_item(
                Key={"user_id": user_id, "window_start": current_day}
            )
            day_count = day_response.get("Item", {}).get("count", 0)

            if day_count >= runtime.free_tier_requests_per_day:
                reset_in = 86400 - (int(now.timestamp()) - current_day)
                return {
                    "allowed": False,
                    "reset_in": reset_in,
                    "message": (
                        f"⏱ Превышен дневной лимит ({runtime.free_tier_requests_per_day}/день).\n"
                        "Попробуйте завтра."
                    ),
                }
        except Exception as exc:
            logger.warning("Error checking daily limit: %s", exc)

        return {"allowed": True, "reset_in": 0, "message": ""}
    except Exception as exc:
        logger.error("Rate limit check error: %s", exc)
        return {"allowed": True, "reset_in": 0, "message": ""}


def increment_rate_limit(user_id: int):
    """Increments the request counter for a user."""
    runtime = get_runtime_services()

    try:
        now = datetime.utcnow()
        current_hour = int(now.timestamp() // 3600) * 3600
        current_day = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        ttl = int(now.timestamp()) + 90000

        try:
            runtime.rate_limits_table.update_item(
                Key={"user_id": user_id, "window_start": current_hour},
                UpdateExpression="ADD #count :inc SET #ttl = :ttl",
                ExpressionAttributeNames={"#count": "count", "#ttl": "ttl"},
                ExpressionAttributeValues={":inc": 1, ":ttl": ttl},
            )
        except Exception as exc:
            logger.error("Error incrementing hourly counter: %s", exc)

        try:
            runtime.rate_limits_table.update_item(
                Key={"user_id": user_id, "window_start": current_day},
                UpdateExpression="ADD #count :inc SET #ttl = :ttl",
                ExpressionAttributeNames={"#count": "count", "#ttl": "ttl"},
                ExpressionAttributeValues={":inc": 1, ":ttl": ttl},
            )
        except Exception as exc:
            logger.error("Error incrementing daily counter: %s", exc)
    except Exception as exc:
        logger.error("Rate limit increment error: %s", exc)


def create_job_record(
    job_id: str,
    user_id: int,
    s3_key: str,
    duration: int,
    chat_id: Optional[int] = None,
    progress_message_id: Optional[int] = None,
):
    """Creates a job record in DynamoDB."""
    runtime = get_runtime_services()

    try:
        item = {
            "job_id": job_id,
            "user_id": user_id,
            "s3_key": s3_key,
            "duration": duration,
            "status": "queued",
            "progress": 0,
            "created_at": datetime.utcnow().isoformat(),
            "ttl": int(datetime.utcnow().timestamp()) + (30 * 24 * 60 * 60),
        }

        if chat_id is not None:
            item["chat_id"] = chat_id
        if progress_message_id is not None:
            item["progress_message_id"] = progress_message_id

        runtime.jobs_table.put_item(Item=item)
        logger.info("Job record created: %s", job_id)
    except Exception as exc:
        logger.error("Error creating DynamoDB record: %s", exc)


def update_job_status(
    job_id: str,
    status: str,
    progress: Optional[int] = None,
    error_message: Optional[str] = None,
):
    """Updates job status."""
    runtime = get_runtime_services()

    try:
        update_expr = "SET #status = :status"
        expr_attr_names = {"#status": "status"}
        expr_attr_values = {":status": status}

        if progress is not None:
            update_expr += ", progress = :progress"
            expr_attr_values[":progress"] = progress

        if error_message is not None:
            update_expr += ", error_message = :error_message"
            expr_attr_values[":error_message"] = error_message

        runtime.jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values,
        )
    except Exception as exc:
        logger.error("Error updating status: %s", exc)


def set_progress_message_id(job_id: str, message_id: int):
    runtime = get_runtime_services()

    try:
        runtime.jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET progress_message_id = :msg_id",
            ExpressionAttributeValues={":msg_id": message_id},
        )
    except Exception as exc:
        logger.error("Error saving progress_message_id: %s", exc)


def generate_presigned_urls(s3_key: str, job_id: str, user_id: int) -> Optional[dict]:
    """
    Generates presigned URLs for S3 operations.
    More secure than sending AWS credentials to RunPod.
    """
    runtime = get_runtime_services()

    try:
        download_url = runtime.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": runtime.s3_bucket, "Key": s3_key},
            ExpiresIn=3600,
        )

        result_key = f"users/{user_id}/results/{job_id}.json"
        upload_url = runtime.s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": runtime.s3_bucket,
                "Key": result_key,
                "ServerSideEncryption": "AES256",
            },
            ExpiresIn=3600,
        )

        return {
            "download_url": download_url,
            "upload_url": upload_url,
            "result_key": result_key,
        }
    except Exception as exc:
        logger.error("Error generating presigned URLs: %s", exc)
        return None


def get_audio_extension(voice, telegram_file) -> str:
    file_name = getattr(voice, "file_name", "") or ""
    if "." in file_name:
        _, ext = os.path.splitext(file_name)
        if ext:
            return ext.lower()

    file_path = getattr(telegram_file, "file_path", "") or ""
    if "." in file_path:
        _, ext = os.path.splitext(file_path)
        if ext:
            return ext.lower()

    mime_type = getattr(voice, "mime_type", None)
    mime_to_ext = {
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".mp4",
        "audio/m4a": ".m4a",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/webm": ".webm",
    }
    return mime_to_ext.get(mime_type, ".ogg")


async def trigger_runpod(job_id: str, s3_key: str, user_id: int, chat_id: int):
    """
    Triggers RunPod serverless endpoint for processing.
    Uses retry with exponential backoff.
    Uses presigned URLs instead of AWS credentials.
    """
    runtime = validate_processing_runtime()
    presigned_urls = generate_presigned_urls(s3_key, job_id, user_id)
    if not presigned_urls:
        logger.error("Failed to generate presigned URLs for job %s", job_id)
        return None

    for attempt in range(runtime.max_retries):
        try:
            wait_time = min(
                runtime.retry_min_wait * (runtime.retry_backoff_multiplier ** attempt),
                runtime.retry_max_wait,
            )

            if attempt > 0:
                logger.info(
                    "Retry %s/%s for job %s, waiting %ss",
                    attempt,
                    runtime.max_retries,
                    job_id,
                    wait_time,
                )
                await asyncio.sleep(wait_time)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{runtime.runpod_endpoint}/run",
                    json={
                        "input": {
                            "job_id": job_id,
                            "s3_bucket": runtime.s3_bucket,
                            "s3_key": s3_key,
                            "audio_download_url": presigned_urls["download_url"],
                            "result_upload_url": presigned_urls["upload_url"],
                            "result_key": presigned_urls["result_key"],
                            "user_id": str(user_id),
                            "chat_id": str(chat_id),
                            "callback_url": runtime.callback_url,
                            "callback_token": runtime.runpod_callback_token,
                        }
                    },
                    headers={"Authorization": f"Bearer {runtime.runpod_api_key}"},
                )

            if response.status_code == 200:
                logger.info("RunPod triggered for job %s", job_id)
                return response.json()

            if response.status_code >= 500:
                logger.warning("RunPod server error %s, will retry", response.status_code)
                continue

            logger.error("RunPod trigger failed: %s %s", response.status_code, response.text)
            return None
        except httpx.TimeoutException:
            logger.warning("RunPod timeout on attempt %s/%s", attempt + 1, runtime.max_retries)
        except httpx.NetworkError as exc:
            logger.warning(
                "RunPod network error on attempt %s/%s: %s",
                attempt + 1,
                runtime.max_retries,
                exc,
            )
        except Exception as exc:
            logger.error("Unexpected error calling RunPod: %s", exc)
            return None

    logger.error("Failed to trigger RunPod after %s attempts for job %s", runtime.max_retries, job_id)
    return None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Привет! Я бот для анализа звонков.*\n\n"
        "📤 *Как использовать:*\n"
        "Просто отправь мне голосовое сообщение или аудиофайл.\n\n"
        "🔄 *Что я делаю:*\n"
        "1️⃣ Расшифровываю текст (транскрипция)\n"
        "2️⃣ Определяю спикеров (кто что сказал)\n"
        "3️⃣ Создаю структурированное саммари:\n"
        "   • Коммерция\n"
        "   • Операционка\n"
        "   • Техника\n"
        "   • Поручения с ответственными\n\n"
        "⏱ *Время обработки:* ~20 минут на 1 час аудио\n\n"
        "📝 *Доступные команды:*\n"
        "/start - Показать это сообщение\n"
        "/status <job_id> - Проверить статус задачи\n"
        "/help - Помощь\n\n"
        "💰 Стоимость: ~$0.15 за час аудио",
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *ПОМОЩЬ*\n\n"
        "*Формат результата:*\n\n"
        "📋 ЧТО ОБСУДИЛИ:\n"
        "• Коммерция - ставки, продажи, клиенты\n"
        "• Операционка - текущие проблемы, балансировка\n"
        "• Техника - интеграции, релизы, L2\n\n"
        "📌 ПОРУЧЕНИЯ:\n"
        "Конкретные задачи с ответственными и сроками\n\n"
        "*Поддерживаемые форматы:*\n"
        "• Голосовые сообщения Telegram\n"
        "• WAV, MP3, OGG, M4A\n"
        "• Максимум: 2 часа аудио\n\n"
        "*Проблемы?*\n"
        "Напишите @your_support",
        parse_mode="Markdown",
    )


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    voice = update.message.voice or update.message.audio

    if not voice:
        return

    try:
        runtime = validate_processing_runtime()
    except RuntimeError as exc:
        logger.error("Runtime configuration error: %s", exc)
        await update.message.reply_text(
            "❌ Сервис сейчас не настроен для обработки аудио.\n"
            "Проверьте конфигурацию и попробуйте позже."
        )
        return

    mime_type = getattr(voice, "mime_type", None)
    if mime_type and mime_type not in SUPPORTED_AUDIO_FORMATS:
        await update.message.reply_text(
            "❌ Неподдерживаемый формат аудио.\n"
            "Поддерживаются: OGG, MP3, MP4, M4A, WAV, WebM."
        )
        return

    rate_limit_check = check_rate_limit(user_id)
    if not rate_limit_check["allowed"]:
        await update.message.reply_text(rate_limit_check["message"])
        logger.warning("Rate limit exceeded for user %s", user_id)
        return

    if voice.duration > runtime.max_audio_duration:
        await update.message.reply_text(
            "❌ Слишком длинное аудио!\n"
            f"Максимум: {runtime.max_audio_duration // 60} минут\n"
            f"Ваше аудио: {voice.duration // 60} минут"
        )
        return

    if voice.duration < runtime.min_audio_duration:
        await update.message.reply_text(
            "❌ Слишком короткое аудио!\n"
            f"Минимум: {runtime.min_audio_duration} секунд"
        )
        return

    if voice.file_size and voice.file_size > runtime.max_file_size_mb * 1024 * 1024:
        await update.message.reply_text(
            "❌ Файл слишком большой!\n"
            f"Максимум: {runtime.max_file_size_mb} MB\n"
            f"Ваш файл: {voice.file_size / (1024 * 1024):.1f} MB"
        )
        return

    job_id = str(uuid.uuid4())
    logger.info("Audio received from user %s, job_id: %s", user_id, job_id)

    await update.message.reply_text(
        f"✅ *Получил аудио!*\n\n"
        f"📊 Длительность: {voice.duration // 60} мин {voice.duration % 60} сек\n"
        f"🔄 Начинаю обработку...\n\n"
        f"📝 ID задачи: `{job_id}`\n"
        f"⏳ Примерное время: ~{estimate_processing_time(voice.duration)} минут\n\n"
        "Пришлю результат, как только будет готово! 📬",
        parse_mode="Markdown",
    )

    try:
        telegram_file = await get_bot().get_file(voice.file_id)
        file_bytes = await telegram_file.download_as_bytearray()
        extension = get_audio_extension(voice, telegram_file)
        s3_key = f"users/{user_id}/audio/new/{job_id}{extension}"

        runtime.s3_client.put_object(
            Bucket=runtime.s3_bucket,
            Key=s3_key,
            Body=bytes(file_bytes),
            ServerSideEncryption="AES256",
            Metadata={
                "telegram_user_id": str(user_id),
                "job_id": job_id,
                "duration": str(voice.duration),
                "chat_id": str(chat_id),
                "mime_type": mime_type or "",
            },
        )

        logger.info("File uploaded to S3: %s", s3_key)
        create_job_record(job_id, user_id, s3_key, voice.duration, chat_id=chat_id)
        increment_rate_limit(user_id)

        runpod_response = await trigger_runpod(job_id, s3_key, user_id, chat_id)
        if not runpod_response:
            error_message = "RunPod endpoint is unavailable or rejected the request."
            update_job_status(job_id, "failed", error_message=error_message)
            await update.message.reply_text(
                "❌ *Не удалось запустить обработку*\n\n"
                "Попробуйте еще раз позже.",
                parse_mode="Markdown",
            )
            return

        update_job_status(job_id, "processing", progress=5)
        progress_msg = await update.message.reply_text(
            "🚀 *Задача запущена!*\n\n"
            "GPU сервер пробудился и начал обработку.\n"
            "Статус будет обновляться в этом сообщении... ⏳",
            parse_mode="Markdown",
        )
        set_progress_message_id(job_id, progress_msg.message_id)
    except RuntimeError as exc:
        logger.error("Voice processing runtime error: %s", exc)
        update_job_status(job_id, "failed", error_message=str(exc))
        await update.message.reply_text(
            "❌ *Сервис не настроен*\n\n"
            "Обработка недоступна до завершения конфигурации.",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Error processing voice message: %s", exc, exc_info=True)
        update_job_status(job_id, "failed", error_message=str(exc))
        await update.message.reply_text(
            "❌ *Ошибка загрузки*\n\n"
            "Попробуйте еще раз или обратитесь в поддержку.",
            parse_mode="Markdown",
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "📊 *Проверка статуса задачи*\n\n"
            "Использование: `/status <job_id>`\n\n"
            "Пример:\n"
            "`/status 123e4567-e89b-12d3-a456-426614174000`",
            parse_mode="Markdown",
        )
        return

    runtime = get_runtime_services()
    job_id = context.args[0]
    user_id = update.effective_user.id

    try:
        response = runtime.jobs_table.get_item(Key={"job_id": job_id})
        if "Item" not in response:
            await update.message.reply_text(
                f"❌ Задача `{job_id}` не найдена.\n\nПроверьте правильность ID.",
                parse_mode="Markdown",
            )
            return

        job = response["Item"]
        if job["user_id"] != user_id:
            await update.message.reply_text("🔒 У вас нет доступа к этой задаче.")
            return

        status = job.get("status", "unknown")
        progress = job.get("progress", 0)
        result_key = f"users/{user_id}/results/{job_id}.json"

        if status in {"queued", "processing"}:
            try:
                result_obj = runtime.s3_client.get_object(Bucket=runtime.s3_bucket, Key=result_key)
                result = json.loads(result_obj["Body"].read())
                result_status = result.get("status")

                if result_status == "completed":
                    update_job_status(job_id, "completed", 100)
                    await send_result_to_user(update.effective_chat.id, result, job_id=job_id)
                    await update.message.reply_text(
                        "✅ Результат уже готов. Отправил его повторно.",
                        parse_mode="Markdown",
                    )
                    return

                if result_status == "failed":
                    error_message = result.get("error", "Неизвестная ошибка")
                    update_job_status(job_id, "failed", error_message=error_message)
                    status = "failed"
            except runtime.s3_client.exceptions.NoSuchKey:
                pass
            except json.JSONDecodeError as exc:
                logger.warning("Invalid result JSON for job %s: %s", job_id, exc)
            except Exception as exc:
                logger.warning("Unexpected status refresh error for job %s: %s", job_id, exc)

        status_emoji = {
            "queued": "⏳",
            "processing": "🔄",
            "completed": "✅",
            "failed": "❌",
        }.get(status, "❓")

        message = (
            f"{status_emoji} *Статус задачи*\n\n"
            f"ID: `{job_id}`\n"
            f"Статус: *{status.upper()}*\n"
            f"Прогресс: {progress}%\n"
            f"Создано: {job.get('created_at', 'N/A')}\n"
        )

        if status == "completed":
            message += "\n✅ Обработка завершена! Результат был отправлен вам."
            try:
                result_obj = runtime.s3_client.get_object(Bucket=runtime.s3_bucket, Key=result_key)
                result = json.loads(result_obj["Body"].read())
                await send_result_to_user(update.effective_chat.id, result, job_id=job_id)
            except (runtime.s3_client.exceptions.NoSuchKey, json.JSONDecodeError) as exc:
                logger.warning("Could not resend result for job %s: %s", job_id, exc)
            except Exception as exc:
                logger.error("Unexpected error resending result: %s", exc)
        elif status == "failed":
            error_msg = job.get("error_message", "Неизвестная ошибка")
            message += f"\n\n❌ Ошибка: {error_msg}"

        await update.message.reply_text(message, parse_mode="Markdown")
    except Exception as exc:
        logger.error("Error retrieving status: %s", exc)
        await update.message.reply_text(
            "❌ Ошибка получения статуса задачи.\nПопробуйте позже."
        )


def split_message(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]

    parts = []
    current = ""
    for line in text.splitlines(keepends=True):
        if current and len(current) + len(line) > limit:
            parts.append(current.rstrip())
            current = line
        else:
            current += line

    if current:
        parts.append(current.rstrip())

    return parts


async def send_result_to_user(chat_id: int, result: dict, job_id: Optional[str] = None):
    runtime = get_runtime_services()

    if job_id:
        try:
            job = runtime.jobs_table.get_item(Key={"job_id": job_id}).get("Item")
            progress_message_id = job.get("progress_message_id") if job else None

            if progress_message_id:
                await get_bot().edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_message_id,
                    text="✅ *Готово!*\n\nОбработка завершена, результаты отправляются...",
                    parse_mode="Markdown",
                )
        except Exception as exc:
            logger.warning("Failed to edit final progress message: %s", exc)

    message = "✅ *ОБРАБОТКА ЗАВЕРШЕНА*\n\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if result.get("discussed"):
        message += "📋 *ЧТО ОБСУДИЛИ:*\n\n"
        discussed = result["discussed"]

        if discussed.get("commerce"):
            message += "💰 *Коммерция*\n"
            message += f"{discussed['commerce']}\n\n"

        if discussed.get("operations"):
            message += "⚙️ *Операционка*\n"
            message += f"{discussed['operations']}\n\n"

        if discussed.get("technical"):
            message += "🔧 *Техника*\n"
            message += f"{discussed['technical']}\n\n"

        message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    if result.get("tasks"):
        message += "📌 *ПОРУЧЕНИЯ:*\n\n"
        tasks = result["tasks"]

        if tasks.get("commerce"):
            message += "💰 *Коммерция:*\n"
            for i, task in enumerate(tasks["commerce"], 1):
                message += f"{i}. {task.get('task', 'N/A')}\n"
                message += f"   👤 {task.get('responsible', 'Не указан')}\n"
                message += f"   ⏰ {task.get('deadline', 'Не указан')}\n"
                if task.get("priority"):
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task["priority"], "")
                    message += f"   {priority_emoji} Приоритет: {task['priority']}\n"
                message += "\n"

        if tasks.get("operations"):
            message += "⚙️ *Операционка:*\n"
            for i, task in enumerate(tasks["operations"], 1):
                message += f"{i}. {task.get('task', 'N/A')}\n"
                message += f"   👤 {task.get('responsible', 'Не указан')}\n"
                message += f"   ⏰ {task.get('deadline', 'Не указан')}\n"
                if task.get("priority"):
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task["priority"], "")
                    message += f"   {priority_emoji} Приоритет: {task['priority']}\n"
                message += "\n"

        if tasks.get("technical"):
            message += "🔧 *Техника:*\n"
            for i, task in enumerate(tasks["technical"], 1):
                message += f"{i}. {task.get('task', 'N/A')}\n"
                message += f"   👤 {task.get('responsible', 'Не указан')}\n"
                message += f"   ⏰ {task.get('deadline', 'Не указан')}\n"
                if task.get("priority"):
                    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task["priority"], "")
                    message += f"   {priority_emoji} Приоритет: {task['priority']}\n"
                message += "\n"

    for part in split_message(message, runtime.telegram_max_message_length):
        await get_bot().send_message(chat_id=chat_id, text=part, parse_mode="Markdown")

    if result.get("full_transcript"):
        await get_bot().send_document(
            chat_id=chat_id,
            document=result["full_transcript"].encode("utf-8"),
            filename="transcript.txt",
            caption="📄 Полная расшифровка с разметкой спикеров",
        )


async def handle_runpod_callback(callback_data: dict):
    try:
        job_id = callback_data.get("job_id")
        chat_id = callback_data.get("chat_id")
        status = callback_data.get("status")

        logger.info("Processing RunPod callback for job %s, status: %s", job_id, status)

        if not job_id or not chat_id:
            logger.error("Missing job_id or chat_id in callback")
            return

        if status == "COMPLETED":
            result = callback_data.get("result")
            if result:
                update_job_status(job_id, "completed", 100)
                await send_result_to_user(int(chat_id), result, job_id=job_id)
                logger.info("Successfully sent results for job %s", job_id)
            else:
                logger.error("No result data in callback for job %s", job_id)
                update_job_status(job_id, "failed", error_message="No result data in callback.")
                await get_bot().send_message(
                    chat_id=int(chat_id),
                    text="❌ Обработка завершилась с ошибкой. Результаты не получены.",
                )
        elif status == "PROGRESS":
            progress = callback_data.get("progress", 0)
            message = callback_data.get("message", "")
            update_job_status(job_id, "processing", progress)

            try:
                runtime = get_runtime_services()
                job = runtime.jobs_table.get_item(Key={"job_id": job_id}).get("Item")
                progress_message_id = job.get("progress_message_id") if job else None

                if progress_message_id and progress in [20, 50, 70]:
                    await get_bot().edit_message_text(
                        chat_id=int(chat_id),
                        message_id=progress_message_id,
                        text=f"🚀 *Задача запущена!*\n\n⏳ {message}\n\nПрогресс: {progress}%",
                        parse_mode="Markdown",
                    )
            except Exception as exc:
                logger.warning("Failed to edit progress message: %s", exc)

            logger.info("Progress update for job %s: %s%% - %s", job_id, progress, message)
        elif status == "FAILED":
            error_msg = callback_data.get("error", "Unknown error")
            update_job_status(job_id, "failed", error_message=error_msg)
            logger.error("Job %s failed: %s", job_id, error_msg)
            await get_bot().send_message(
                chat_id=int(chat_id),
                text=f"❌ Обработка завершилась с ошибкой:\n{error_msg}",
            )
        else:
            logger.warning("Unknown callback status: %s", status)
    except Exception as exc:
        logger.error("Error processing RunPod callback: %s", exc, exc_info=True)


def get_header(headers: Optional[dict], name: str) -> str:
    if not headers:
        return ""

    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return ""


def parse_event_body(event: dict) -> dict:
    body = event.get("body")
    if body is None:
        return event

    if event.get("isBase64Encoded"):
        raise ValueError("Base64 encoded payloads are not supported.")

    return json.loads(body or "{}")


async def process_telegram_webhook(body: dict):
    application = build_application()

    try:
        await application.initialize()
        update = Update.de_json(body, get_bot())
        await application.process_update(update)
    finally:
        await application.shutdown()


def lambda_handler(event, context):
    body = {}

    try:
        body = parse_event_body(event)

        logger.info(
            "Lambda invoked: keys=%s, body_keys=%s",
            sorted(event.keys()),
            sorted(body.keys()) if isinstance(body, dict) else [],
        )

        is_runpod_callback = isinstance(body, dict) and "job_id" in body and "status" in body
        is_telegram_webhook = isinstance(body, dict) and ("update_id" in body or "message" in body)

        if is_runpod_callback:
            runtime = get_runtime_services()
            received_token = get_header(event.get("headers", {}), RUNPOD_CALLBACK_HEADER)
            if not runtime.runpod_callback_token or received_token != runtime.runpod_callback_token:
                logger.warning("Rejected unauthenticated RunPod callback for job %s", body.get("job_id"))
                return {"statusCode": 403, "body": json.dumps("Forbidden")}

            asyncio.run(handle_runpod_callback(body))
        elif is_telegram_webhook:
            runtime = get_runtime_services()
            if runtime.telegram_secret_token:
                received_token = get_header(
                    event.get("headers", {}),
                    "x-telegram-bot-api-secret-token",
                )
                if received_token != runtime.telegram_secret_token:
                    logger.warning("Invalid Telegram secret token")
                    return {"statusCode": 403, "body": json.dumps("Forbidden")}

            asyncio.run(process_telegram_webhook(body))
        else:
            logger.warning("Unknown event type: %s", body)

        return {"statusCode": 200, "body": json.dumps("OK")}
    except Exception as exc:
        logger.error("Lambda handler error: %s", exc, exc_info=True)
        return {"statusCode": 500, "body": json.dumps("Server error")}


if __name__ == "__main__":
    print("For local testing use polling mode")
    print("Run: python3 telegram_bot/bot_local.py")
