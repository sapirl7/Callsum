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

# AWS клиенты
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
secrets_client = boto3.client('secretsmanager')
dynamodb = boto3.resource('dynamodb')

# Конфигурация из переменных окружения
S3_BUCKET = os.getenv('S3_BUCKET_NAME', 'callsum-prod')
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')
DYNAMODB_TABLE = os.getenv('DYNAMODB_TABLE_NAME', 'callsum-jobs')
RUNPOD_ENDPOINT = os.getenv('RUNPOD_ENDPOINT_URL')
RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')

# Таблица DynamoDB
jobs_table = dynamodb.Table(DYNAMODB_TABLE)


def get_telegram_token():
    """Получает Telegram Bot Token из AWS Secrets Manager"""
    try:
        response = secrets_client.get_secret_value(SecretId='telegram-bot-token')
        secret = json.loads(response['SecretString'])
        return secret['token']
    except Exception as e:
        logger.error(f"Ошибка получения токена: {e}")
        # Fallback на переменную окружения для локальной разработки
        return os.getenv('TELEGRAM_BOT_TOKEN')


BOT_TOKEN = get_telegram_token()
bot = Bot(token=BOT_TOKEN)


# ===== HELPER FUNCTIONS =====

def estimate_processing_time(duration_seconds: int) -> int:
    """
    Оценивает время обработки аудио.

    1 час аудио ≈ 20 минут обработки на RTX 3090
    """
    return max(1, int(duration_seconds / 60 * 0.33))


def create_job_record(job_id: str, user_id: int, s3_key: str, duration: int):
    """Создает запись о задаче в DynamoDB"""
    try:
        jobs_table.put_item(
            Item={
                'job_id': job_id,
                'user_id': user_id,
                's3_key': s3_key,
                'duration': duration,
                'status': 'queued',
                'progress': 0,
                'created_at': datetime.utcnow().isoformat(),
                'ttl': int(datetime.utcnow().timestamp()) + (30 * 24 * 60 * 60)  # 30 дней
            }
        )
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


async def trigger_runpod(job_id: str, s3_key: str, user_id: int, chat_id: int):
    """Пробуждает RunPod serverless endpoint для обработки"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{RUNPOD_ENDPOINT}/run",
                json={
                    'input': {
                        'job_id': job_id,
                        's3_bucket': S3_BUCKET,
                        's3_key': s3_key,
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
            else:
                logger.error(f"RunPod trigger failed: {response.status_code} {response.text}")
                return None

    except Exception as e:
        logger.error(f"Ошибка вызова RunPod: {e}")
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

    # Проверка длительности (макс 2 часа)
    if voice.duration > 7200:
        await update.message.reply_text(
            "❌ Слишком длинное аудио!\n"
            "Максимум: 2 часа (120 минут)\n"
            f"Ваше аудио: {voice.duration // 60} минут"
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

        # 3. Создаем запись в DynamoDB
        create_job_record(job_id, user_id, s3_key, voice.duration)

        # 4. Отправляем задачу в SQS
        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps({
                'job_id': job_id,
                's3_key': s3_key,
                'user_id': user_id,
                'chat_id': chat_id,
                'duration': voice.duration
            }),
            MessageAttributes={
                'job_id': {'StringValue': job_id, 'DataType': 'String'},
                'user_id': {'StringValue': str(user_id), 'DataType': 'String'}
            }
        )

        logger.info(f"Задача отправлена в SQS: {job_id}")

        # 5. Триггерим RunPod serverless endpoint
        runpod_response = await trigger_runpod(job_id, s3_key, user_id, chat_id)

        if runpod_response:
            update_job_status(job_id, 'processing', progress=5)
            await update.message.reply_text(
                "🚀 *Задача запущена!*\n\n"
                "GPU сервер пробудился и начал обработку.\n"
                "Вы получите уведомление когда всё будет готово! ⏳",
                parse_mode='Markdown'
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
            except:
                pass

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


async def send_result_to_user(chat_id: int, result: dict):
    """
    Отправляет результат обработки пользователю в Telegram.

    Формат соответствует требованиям:
    - ЧТО ОБСУДИЛИ (3 блока)
    - ПОРУЧЕНИЯ (3 блока с задачами)
    """

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

def lambda_handler(event, context):
    """
    Entry point для AWS Lambda.
    Вызывается когда приходит webhook от Telegram.
    """
    logger.info(f"Lambda invoked with event: {json.dumps(event)}")

    try:
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()

        # Регистрируем handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(MessageHandler(filters.VOICE, voice_handler))

        # Обрабатываем webhook от Telegram
        if 'body' in event:
            update = Update.de_json(json.loads(event['body']), bot)

            # Запускаем обработку в event loop
            asyncio.run(application.process_update(update))

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
