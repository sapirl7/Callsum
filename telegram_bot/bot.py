# -*- coding: utf-8 -*-
"""
Telegram Bot для приема голосовых сообщений и отправки результатов.
Деплоится как AWS Lambda функция.
"""
import os
import json
import boto3
import logging
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
import uuid
import httpx
import asyncio

# Настройка логирования
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Поддерживаемые аудио форматы
SUPPORTED_AUDIO_FORMATS = {
    'audio/ogg',
    'audio/mpeg',
    'audio/mp3',
    'audio/mp4',
    'audio/m4a',
    'audio/wav',
    'audio/x-wav',
    'audio/webm'
}

# AWS / S3-compatible клиенты
# Поддержка DigitalOcean Spaces и других S3-совместимых хранилищ
s3_config = {
    'service_name': 's3',
    'region_name': os.getenv('AWS_REGION', 'us-east-1')
}

# Если указан кастомный endpoint (например, DigitalOcean Spaces)
if os.getenv('S3_ENDPOINT_URL'):
    s3_config['endpoint_url'] = os.getenv('S3_ENDPOINT_URL')
    # Используем явные credentials для DO Spaces
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        s3_config['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID')
        s3_config['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY')

s3_client = boto3.client(**s3_config)
secrets_client = boto3.client('secretsmanager')
dynamodb = boto3.resource('dynamodb')

# Конфигурация из переменных окружения
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'callsum-prod')
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE_NAME', 'callsum-jobs')
RATE_LIMITS_TABLE = os.getenv('RATE_LIMITS_TABLE_NAME', 'callsum-jobs-rate-limits')
RUNPOD_ENDPOINT = os.getenv('RUNPOD_ENDPOINT_URL')

# Application configuration
MAX_AUDIO_DURATION = int(os.getenv('MAX_AUDIO_DURATION_SECONDS', '7200'))
MIN_AUDIO_DURATION = int(os.getenv('MIN_AUDIO_DURATION_SECONDS', '1'))
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '100'))
FREE_TIER_REQUESTS_PER_HOUR = int(os.getenv('FREE_TIER_REQUESTS_PER_HOUR', '10'))
FREE_TIER_REQUESTS_PER_DAY = int(os.getenv('FREE_TIER_REQUESTS_PER_DAY', '50'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_BACKOFF_MULTIPLIER = int(os.getenv('RETRY_BACKOFF_MULTIPLIER', '2'))
RETRY_MIN_WAIT = int(os.getenv('RETRY_MIN_WAIT_SECONDS', '2'))
RETRY_MAX_WAIT = int(os.getenv('RETRY_MAX_WAIT_SECONDS', '10'))
TELEGRAM_MAX_MESSAGE_LENGTH = int(os.getenv('TELEGRAM_MAX_MESSAGE_LENGTH', '4000'))

# Таблицы DynamoDB
jobs_table = dynamodb.Table(DYNAMODB_TABLE)
rate_limits_table = dynamodb.Table(RATE_LIMITS_TABLE)


def get_secret(secret_arn: str, key: str, fallback_env_var: str = None):
    """
    Получает секрет из AWS Secrets Manager.

    Args:
        secret_arn: ARN секрета в Secrets Manager
        key: Ключ в JSON секрета
        fallback_env_var: Переменная окружения для fallback
    """
    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        return secret.get(key)
    except Exception as e:
        logger.error(f"Ошибка получения секрета {secret_arn}: {e}")
        # Fallback на переменную окружения для локальной разработки
        if fallback_env_var:
            return os.getenv(fallback_env_var)
        return None


def get_telegram_token():
    """Получает Telegram Bot Token из AWS Secrets Manager"""
    telegram_secret_arn = os.getenv('TELEGRAM_BOT_TOKEN_SECRET_ARN')
    if telegram_secret_arn:
        return get_secret(telegram_secret_arn, 'token', 'TELEGRAM_BOT_TOKEN')
    return os.getenv('TELEGRAM_BOT_TOKEN')


def get_runpod_api_key():
    """Получает RunPod API Key из AWS Secrets Manager"""
    runpod_secret_arn = os.getenv('RUNPOD_API_KEY_SECRET_ARN')
    if runpod_secret_arn:
        return get_secret(runpod_secret_arn, 'api_key', 'RUNPOD_API_KEY')
    return os.getenv('RUNPOD_API_KEY')


BOT_TOKEN = get_telegram_token()
RUNPOD_API_KEY = get_runpod_api_key()
TELEGRAM_SECRET_TOKEN = os.getenv('TELEGRAM_SECRET_TOKEN', '')  # Secret token для защиты webhook
bot = Bot(token=BOT_TOKEN)


# ===== HELPER FUNCTIONS =====

def estimate_processing_time(duration_seconds: int) -> int:
    """
    Оценивает время обработки аудио.

    1 час аудио ≈ 20 минут обработки на RTX 3090
    """
    return max(1, int(duration_seconds / 60 * 0.33))


def check_rate_limit(user_id: int) -> dict:
    """
    Проверяет rate limit для пользователя.

    Returns:
        dict: {'allowed': bool, 'reset_in': int (seconds), 'message': str}
    """
    try:
        now = datetime.utcnow()
        current_hour = int(now.timestamp() // 3600) * 3600
        current_day = int(now.replace(hour=0, minute=0, second=0).timestamp())

        # Проверяем hourly limit
        try:
            hour_response = rate_limits_table.get_item(
                Key={'user_id': user_id, 'window_start': current_hour}
            )
            hour_count = hour_response.get('Item', {}).get('count', 0)

            if hour_count >= FREE_TIER_REQUESTS_PER_HOUR:
                reset_in = 3600 - (int(now.timestamp()) - current_hour)
                return {
                    'allowed': False,
                    'reset_in': reset_in,
                    'message': f"⏱ Превышен лимит запросов в час ({FREE_TIER_REQUESTS_PER_HOUR}/час).\nПопробуйте через {reset_in // 60} мин."
                }
        except Exception as e:
            logger.warning(f"Error checking hourly limit: {e}")

        # Проверяем daily limit
        try:
            day_response = rate_limits_table.get_item(
                Key={'user_id': user_id, 'window_start': current_day}
            )
            day_count = day_response.get('Item', {}).get('count', 0)

            if day_count >= FREE_TIER_REQUESTS_PER_DAY:
                reset_in = 86400 - (int(now.timestamp()) - current_day)
                return {
                    'allowed': False,
                    'reset_in': reset_in,
                    'message': f"⏱ Превышен дневной лимит ({FREE_TIER_REQUESTS_PER_DAY}/день).\nПопробуйте завтра."
                }
        except Exception as e:
            logger.warning(f"Error checking daily limit: {e}")

        return {'allowed': True, 'reset_in': 0, 'message': ''}

    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        # В случае ошибки разрешаем (fail open)
        return {'allowed': True, 'reset_in': 0, 'message': ''}


def increment_rate_limit(user_id: int):
    """Инкрементирует счетчик запросов для пользователя."""
    try:
        now = datetime.utcnow()
        current_hour = int(now.timestamp() // 3600) * 3600
        current_day = int(now.replace(hour=0, minute=0, second=0).timestamp())

        # TTL = через 25 часов (чтобы точно покрыть весь день)
        ttl = int(now.timestamp()) + 90000

        # Инкремент hourly counter
        try:
            rate_limits_table.update_item(
                Key={'user_id': user_id, 'window_start': current_hour},
                UpdateExpression='ADD #count :inc SET #ttl = :ttl',
                ExpressionAttributeNames={'#count': 'count', '#ttl': 'ttl'},
                ExpressionAttributeValues={':inc': 1, ':ttl': ttl}
            )
        except Exception as e:
            logger.error(f"Error incrementing hourly counter: {e}")

        # Инкремент daily counter
        try:
            rate_limits_table.update_item(
                Key={'user_id': user_id, 'window_start': current_day},
                UpdateExpression='ADD #count :inc SET #ttl = :ttl',
                ExpressionAttributeNames={'#count': 'count', '#ttl': 'ttl'},
                ExpressionAttributeValues={':inc': 1, ':ttl': ttl}
            )
        except Exception as e:
            logger.error(f"Error incrementing daily counter: {e}")

    except Exception as e:
        logger.error(f"Rate limit increment error: {e}")


def create_job_record(job_id: str, user_id: int, s3_key: str, duration: int, chat_id: int = None, progress_message_id: int = None):
    """Создает запись о задаче в DynamoDB"""
    try:
        item = {
            'job_id': job_id,
            'user_id': user_id,
            's3_key': s3_key,
            'duration': duration,
            'status': 'queued',
            'progress': 0,
            'created_at': datetime.utcnow().isoformat(),
            'ttl': int(datetime.utcnow().timestamp()) + (30 * 24 * 60 * 60)  # 30 дней
        }

        # Добавляем опциональные поля для редактирования прогресс-сообщения
        if chat_id is not None:
            item['chat_id'] = chat_id
        if progress_message_id is not None:
            item['progress_message_id'] = progress_message_id

        jobs_table.put_item(Item=item)
        logger.info(f"Создана запись задачи {job_id}")
    except Exception as e:
        logger.error(f"Ошибка создания записи в DynamoDB: {e}")


def update_job_status(job_id: str, status: str, progress: int = None):
    """Обновляет статус задачи"""
    try:
        update_expr = "SET #status = :status"
        expr_attr_names = {"#status": "status"}
        expr_attr_values = {":status": status}

        if progress is not None:
            update_expr += ", progress = :progress"
            expr_attr_values[":progress"] = progress

        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )
    except Exception as e:
        logger.error(f"Ошибка обновления статуса: {e}")


def generate_presigned_urls(s3_key: str, job_id: str, user_id: int) -> dict:
    """
    Генерирует presigned URLs для S3 операций.
    Безопаснее чем отправлять AWS credentials в RunPod.

    Returns:
        dict: {'download_url': str, 'upload_url': str}
    """
    try:
        # URL для скачивания аудио (действителен 1 час)
        download_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=3600
        )

        # URL для загрузки результата (действителен 1 час)
        result_key = f"users/{user_id}/results/{job_id}.json"
        upload_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': result_key,
                'ServerSideEncryption': 'AES256'
            },
            ExpiresIn=3600
        )

        return {
            'download_url': download_url,
            'upload_url': upload_url,
            'result_key': result_key
        }
    except Exception as e:
        logger.error(f"Error generating presigned URLs: {e}")
        return None


async def trigger_runpod(job_id: str, s3_key: str, user_id: int, chat_id: int):
    """
    Пробуждает RunPod serverless endpoint для обработки.
    Использует retry с exponential backoff.
    Использует presigned URLs вместо AWS credentials.
    """
    # Генерируем presigned URLs
    presigned_urls = generate_presigned_urls(s3_key, job_id, user_id)
    if not presigned_urls:
        logger.error(f"Failed to generate presigned URLs for job {job_id}")
        return None

    for attempt in range(MAX_RETRIES):
        try:
            wait_time = min(
                RETRY_MIN_WAIT * (RETRY_BACKOFF_MULTIPLIER ** attempt),
                RETRY_MAX_WAIT
            )

            if attempt > 0:
                logger.info(f"Retry {attempt}/{MAX_RETRIES} for job {job_id}, waiting {wait_time}s")
                await asyncio.sleep(wait_time)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{RUNPOD_ENDPOINT}/run",
                    json={
                        'input': {
                            'job_id': job_id,
                            's3_bucket': S3_BUCKET,
                            's3_key': s3_key,
                            'audio_download_url': presigned_urls['download_url'],
                            'result_upload_url': presigned_urls['upload_url'],
                            'result_key': presigned_urls['result_key'],
                            'user_id': str(user_id),
                            'chat_id': str(chat_id),
                            'callback_url': os.getenv('CALLBACK_URL')  # Для webhook результатов
                        }
                    },
                    headers={'Authorization': f"Bearer {RUNPOD_API_KEY}"}
                )

                if response.status_code == 200:
                    logger.info(f"RunPod triggered for job {job_id}")
                    return response.json()
                elif response.status_code >= 500:
                    # Server error - retry
                    logger.warning(f"RunPod server error {response.status_code}, will retry")
                    continue
                else:
                    # Client error - don't retry
                    logger.error(f"RunPod trigger failed: {response.status_code} {response.text}")
                    return None

        except httpx.TimeoutException:
            logger.warning(f"RunPod timeout on attempt {attempt + 1}/{MAX_RETRIES}")
            continue
        except httpx.NetworkError as e:
            logger.warning(f"RunPod network error on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error calling RunPod: {e}")
            return None

    logger.error(f"Failed to trigger RunPod after {MAX_RETRIES} attempts for job {job_id}")
    return None


# ===== TELEGRAM HANDLERS =====

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
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
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
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
        parse_mode='Markdown'
    )


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик голосовых сообщений"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    voice = update.message.voice

    # Проверка rate limit
    rate_limit_check = check_rate_limit(user_id)
    if not rate_limit_check['allowed']:
        await update.message.reply_text(rate_limit_check['message'])
        logger.warning(f"Rate limit exceeded for user {user_id}")
        return

    # Проверка длительности
    if voice.duration > MAX_AUDIO_DURATION:
        await update.message.reply_text(
            "❌ Слишком длинное аудио!\n"
            f"Максимум: {MAX_AUDIO_DURATION // 60} минут\n"
            f"Ваше аудио: {voice.duration // 60} минут"
        )
        return

    if voice.duration < MIN_AUDIO_DURATION:
        await update.message.reply_text(
            "❌ Слишком короткое аудио!\n"
            f"Минимум: {MIN_AUDIO_DURATION} секунд"
        )
        return

    # Проверка размера файла
    if voice.file_size and voice.file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await update.message.reply_text(
            "❌ Файл слишком большой!\n"
            f"Максимум: {MAX_FILE_SIZE_MB} MB\n"
            f"Ваш файл: {voice.file_size / (1024 * 1024):.1f} MB"
        )
        return

    # Генерируем уникальный ID задачи
    job_id = str(uuid.uuid4())

    logger.info(f"Получено голосовое от user {user_id}, job_id: {job_id}")

    # Уведомление пользователя
    await update.message.reply_text(
        f"✅ *Получил аудио!*\n\n"
        f"📊 Длительность: {voice.duration // 60} мин {voice.duration % 60} сек\n"
        f"🔄 Начинаю обработку...\n\n"
        f"📝 ID задачи: `{job_id}`\n"
        f"⏳ Примерное время: ~{estimate_processing_time(voice.duration)} минут\n\n"
        f"Пришлю результат, как только будет готово! 📬",
        parse_mode='Markdown'
    )

    try:
        # 1. Скачиваем файл из Telegram
        file = await bot.get_file(voice.file_id)
        file_bytes = await file.download_as_bytearray()

        # 2. Загружаем в S3 с шифрованием
        s3_key = f"users/{user_id}/audio/new/{job_id}.ogg"

        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=bytes(file_bytes),
            ServerSideEncryption='AES256',  # Шифрование!
            Metadata={
                'telegram_user_id': str(user_id),
                'job_id': job_id,
                'duration': str(voice.duration),
                'chat_id': str(chat_id)
            }
        )

        logger.info(f"Файл загружен в S3: {s3_key}")

        # 3. Создаем запись в DynamoDB (без progress_message_id пока)
        create_job_record(job_id, user_id, s3_key, voice.duration, chat_id=chat_id)

        # 3.1 Инкрементируем rate limit (после успешного создания задачи)
        increment_rate_limit(user_id)

        # 4. Триггерим RunPod serverless endpoint напрямую (с автоматическим callback)
        runpod_response = await trigger_runpod(job_id, s3_key, user_id, chat_id)

        if runpod_response:
            update_job_status(job_id, 'processing', progress=5)
            # Отправляем начальное сообщение и сохраняем его ID для последующего редактирования
            progress_msg = await update.message.reply_text(
                "🚀 *Задача запущена!*\n\n"
                "GPU сервер пробудился и начал обработку.\n"
                "Статус будет обновляться в этом сообщении... ⏳",
                parse_mode='Markdown'
            )
            # Обновляем запись в DynamoDB с message_id для редактирования
            jobs_table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET progress_message_id = :msg_id',
                ExpressionAttributeValues={':msg_id': progress_msg.message_id}
            )
        else:
            update_job_status(job_id, 'queued')
            await update.message.reply_text(
                "✅ *Задача в очереди*\n\n"
                "Обработка начнется в течение нескольких минут.\n"
                f"Проверить статус: /status {job_id}",
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Ошибка обработки голосового: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ *Ошибка загрузки*\n\n"
            f"Попробуйте еще раз или обратитесь в поддержку.\n"
            f"Код ошибки: {str(e)[:100]}",
            parse_mode='Markdown'
        )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status"""
    if not context.args:
        await update.message.reply_text(
            "📊 *Проверка статуса задачи*\n\n"
            "Использование: `/status <job_id>`\n\n"
            "Пример:\n"
            "`/status 123e4567-e89b-12d3-a456-426614174000`",
            parse_mode='Markdown'
        )
        return

    job_id = context.args[0]
    user_id = update.effective_user.id

    try:
        # Получаем данные из DynamoDB
        response = jobs_table.get_item(Key={'job_id': job_id})

        if 'Item' not in response:
            await update.message.reply_text(
                f"❌ Задача `{job_id}` не найдена.\n\n"
                "Проверьте правильность ID.",
                parse_mode='Markdown'
            )
            return

        job = response['Item']

        # Проверка доступа (пользователь может видеть только свои задачи)
        if job['user_id'] != user_id:
            await update.message.reply_text(
                "🔒 У вас нет доступа к этой задаче."
            )
            return

        # Формируем сообщение о статусе
        status = job.get('status', 'unknown')
        progress = job.get('progress', 0)

        status_emoji = {
            'queued': '⏳',
            'processing': '🔄',
            'completed': '✅',
            'failed': '❌'
        }.get(status, '❓')

        message = (
            f"{status_emoji} *Статус задачи*\n\n"
            f"ID: `{job_id}`\n"
            f"Статус: *{status.upper()}*\n"
            f"Прогресс: {progress}%\n"
            f"Создано: {job.get('created_at', 'N/A')}\n"
        )

        if status == 'completed':
            message += "\n✅ Обработка завершена! Результат был отправлен вам."

            # Пробуем отправить результат еще раз
            result_key = f"users/{user_id}/results/{job_id}.json"
            try:
                result_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=result_key)
                result = json.loads(result_obj['Body'].read())
                await send_result_to_user(update.effective_chat.id, result)
            except (s3_client.exceptions.NoSuchKey, json.JSONDecodeError) as e:
                logger.warning(f"Could not resend result for job {job_id}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error resending result: {e}")

        elif status == 'failed':
            error_msg = job.get('error_message', 'Неизвестная ошибка')
            message += f"\n\n❌ Ошибка: {error_msg}"

        await update.message.reply_text(message, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Ошибка получения статуса: {e}")
        await update.message.reply_text(
            "❌ Ошибка получения статуса задачи.\n"
            "Попробуйте позже."
        )


async def send_result_to_user(chat_id: int, result: dict, job_id: str = None):
    """
    Отправляет результат обработки пользователю в Telegram.

    Формат соответствует требованиям:
    - ЧТО ОБСУДИЛИ (3 блока)
    - ПОРУЧЕНИЯ (3 блока с задачами)
    """

    # Редактируем прогресс-сообщение на "✅ Готово!" перед отправкой полных результатов
    if job_id:
        try:
            job = jobs_table.get_item(Key={'job_id': job_id}).get('Item')
            progress_message_id = job.get('progress_message_id') if job else None

            if progress_message_id:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=progress_message_id,
                    text="✅ *Готово!*\n\nОбработка завершена, результаты отправляются...",
                    parse_mode='Markdown'
                )
        except Exception as edit_error:
            logger.warning(f"Failed to edit final progress message: {edit_error}")

    # Формируем красивое сообщение
    message = "✅ *ОБРАБОТКА ЗАВЕРШЕНА*\n\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # === ЧТО ОБСУДИЛИ ===
    if result.get('discussed'):
        message += "📋 *ЧТО ОБСУДИЛИ:*\n\n"

        discussed = result['discussed']

        if discussed.get('commerce'):
            message += "💰 *Коммерция*\n"
            message += f"{discussed['commerce']}\n\n"

        if discussed.get('operations'):
            message += "⚙️ *Операционка*\n"
            message += f"{discussed['operations']}\n\n"

        if discussed.get('technical'):
            message += "🔧 *Техника*\n"
            message += f"{discussed['technical']}\n\n"

        message += "━━━━━━━━━━━━━━━━━━━━\n\n"

    # === ПОРУЧЕНИЯ ===
    if result.get('tasks'):
        message += "📌 *ПОРУЧЕНИЯ:*\n\n"

        tasks = result['tasks']

        if tasks.get('commerce'):
            message += "💰 *Коммерция:*\n"
            for i, task in enumerate(tasks['commerce'], 1):
                message += f"{i}. {task.get('task', 'N/A')}\n"
                message += f"   👤 {task.get('responsible', 'Не указан')}\n"
                message += f"   ⏰ {task.get('deadline', 'Не указан')}\n"
                if task.get('priority'):
                    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(task['priority'], '')
                    message += f"   {priority_emoji} Приоритет: {task['priority']}\n"
                message += "\n"

        if tasks.get('operations'):
            message += "⚙️ *Операционка:*\n"
            for i, task in enumerate(tasks['operations'], 1):
                message += f"{i}. {task.get('task', 'N/A')}\n"
                message += f"   👤 {task.get('responsible', 'Не указан')}\n"
                message += f"   ⏰ {task.get('deadline', 'Не указан')}\n"
                if task.get('priority'):
                    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(task['priority'], '')
                    message += f"   {priority_emoji} Приоритет: {task['priority']}\n"
                message += "\n"

        if tasks.get('technical'):
            message += "🔧 *Техника:*\n"
            for i, task in enumerate(tasks['technical'], 1):
                message += f"{i}. {task.get('task', 'N/A')}\n"
                message += f"   👤 {task.get('responsible', 'Не указан')}\n"
                message += f"   ⏰ {task.get('deadline', 'Не указан')}\n"
                if task.get('priority'):
                    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(task['priority'], '')
                    message += f"   {priority_emoji} Приоритет: {task['priority']}\n"
                message += "\n"

    # Отправляем (разбиваем если слишком длинное)
    if len(message) > 4096:
        parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for part in parts:
            await bot.send_message(chat_id=chat_id, text=part, parse_mode='Markdown')
    else:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

    # Отправляем полную транскрипцию как файл
    if result.get('full_transcript'):
        transcript_text = result['full_transcript']
        await bot.send_document(
            chat_id=chat_id,
            document=transcript_text.encode('utf-8'),
            filename='transcript.txt',
            caption='📄 Полная расшифровка с разметкой спикеров'
        )


# ===== AWS LAMBDA HANDLER =====

async def handle_runpod_callback(callback_data: dict):
    """
    Обрабатывает callback от RunPod с результатами обработки.

    Args:
        callback_data: Данные от RunPod с результатами
    """
    try:
        job_id = callback_data.get('job_id')
        chat_id = callback_data.get('chat_id')
        status = callback_data.get('status')

        logger.info(f"Processing RunPod callback for job {job_id}, status: {status}")

        if not job_id or not chat_id:
            logger.error("Missing job_id or chat_id in callback")
            return

        # Обновляем статус в DynamoDB
        if status == 'COMPLETED':
            result = callback_data.get('result')
            if result:
                update_job_status(job_id, 'completed', 100)
                await send_result_to_user(int(chat_id), result, job_id=job_id)
                logger.info(f"Successfully sent results for job {job_id}")
            else:
                logger.error(f"No result data in callback for job {job_id}")
                update_job_status(job_id, 'failed')
                await bot.send_message(
                    chat_id=int(chat_id),
                    text="❌ Обработка завершилась с ошибкой. Результаты не получены."
                )
        elif status == 'PROGRESS':
            # Промежуточное обновление прогресса
            progress = callback_data.get('progress', 0)
            message = callback_data.get('message', '')
            update_job_status(job_id, 'processing', progress)

            # Редактируем то же сообщение для UX (вместо спама новыми сообщениями)
            try:
                job = jobs_table.get_item(Key={'job_id': job_id}).get('Item')
                progress_message_id = job.get('progress_message_id') if job else None

                if progress_message_id and progress in [20, 50, 70]:  # Только на ключевых этапах
                    await bot.edit_message_text(
                        chat_id=int(chat_id),
                        message_id=progress_message_id,
                        text=f"🚀 *Задача запущена!*\n\n⏳ {message}\n\nПрогресс: {progress}%",
                        parse_mode='Markdown'
                    )
            except Exception as edit_error:
                logger.warning(f"Failed to edit progress message: {edit_error}")

            logger.info(f"Progress update for job {job_id}: {progress}% - {message}")

        elif status == 'FAILED':
            error_msg = callback_data.get('error', 'Unknown error')
            update_job_status(job_id, 'failed')
            logger.error(f"Job {job_id} failed: {error_msg}")
            await bot.send_message(
                chat_id=int(chat_id),
                text=f"❌ Обработка завершилась с ошибкой:\n{error_msg}"
            )
        else:
            logger.warning(f"Unknown callback status: {status}")

    except Exception as e:
        logger.error(f"Error processing RunPod callback: {e}", exc_info=True)


def lambda_handler(event, context):
    """
    Entry point для AWS Lambda.
    Обрабатывает:
    1. Webhook от Telegram (новые сообщения)
    2. Callback от RunPod (результаты обработки)
    """
    logger.info(f"Lambda invoked with event: {json.dumps(event)}")

    try:
        body = json.loads(event.get('body', '{}')) if 'body' in event else event

        # Определяем тип события
        is_runpod_callback = 'job_id' in body and 'status' in body
        is_telegram_webhook = 'update_id' in body or 'message' in body

        if is_runpod_callback:
            # Обрабатываем callback от RunPod
            logger.info("Detected RunPod callback")
            asyncio.run(handle_runpod_callback(body))

        elif is_telegram_webhook or 'body' in event:
            # Обрабатываем webhook от Telegram
            logger.info("Detected Telegram webhook")

            # SECURITY: Проверяем secret token от Telegram
            if TELEGRAM_SECRET_TOKEN:
                headers = event.get('headers', {})
                # API Gateway может преобразовывать заголовки в lowercase
                received_token = headers.get('X-Telegram-Bot-Api-Secret-Token') or headers.get('x-telegram-bot-api-secret-token', '')

                if received_token != TELEGRAM_SECRET_TOKEN:
                    logger.warning(f"Invalid secret token from {headers.get('X-Forwarded-For', 'unknown')}")
                    return {
                        'statusCode': 403,
                        'body': json.dumps('Forbidden')
                    }

            application = Application.builder().token(BOT_TOKEN).build()

            # Регистрируем handlers
            application.add_handler(CommandHandler("start", start_command))
            application.add_handler(CommandHandler("help", help_command))
            application.add_handler(CommandHandler("status", status_command))
            application.add_handler(MessageHandler(filters.VOICE, voice_handler))

            # Обрабатываем webhook от Telegram
            if 'body' in event:
                update = Update.de_json(json.loads(event['body']), bot)
            else:
                update = Update.de_json(body, bot)

            # Запускаем обработку в event loop
            asyncio.run(application.process_update(update))

        else:
            logger.warning(f"Unknown event type: {body}")

        return {
            'statusCode': 200,
            'body': json.dumps('OK')
        }

    except Exception as e:
        logger.error(f"Lambda handler error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }


# Для локального тестирования
if __name__ == "__main__":
    print("Для локального тестирования используйте polling режим")
    print("Запустите: python bot_local.py")
