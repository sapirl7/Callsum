# -*- coding: utf-8 -*-
"""
RunPod Serverless Handler - обработка аудио через ML модели.
Выполняет транскрипцию, диаризацию и генерацию саммари.
"""
import os
import json
import torch
import boto3
import tempfile
import logging
import httpx
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
from vllm import LLM, SamplingParams

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AWS клиент
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

# Определение устройства
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Используется устройство: {DEVICE}")

# === ЗАГРУЗКА МОДЕЛЕЙ (при старте контейнера) ===

logger.info("Загрузка Whisper...")
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
whisper_model = WhisperModel(
    "large-v3",
    device=DEVICE,
    compute_type=COMPUTE_TYPE,
    download_root="/models/whisper"  # Кэш моделей
)
logger.info("Whisper загружен ✓")

logger.info("Загрузка Pyannote...")
HF_TOKEN = os.getenv('HF_TOKEN')
diarization_pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=HF_TOKEN,
    cache_dir="/models/pyannote"
)
diarization_pipeline.to(torch.device(DEVICE))
logger.info("Pyannote загружен ✓")

logger.info("Загрузка Llama 3...")
llm = LLM(
    model="meta-llama/Meta-Llama-3-70B-Instruct",
    download_dir="/models/llama",
    tensor_parallel_size=1,  # Используем 1 GPU
    gpu_memory_utilization=0.9
)
logger.info("Llama 3 загружен ✓")

logger.info("Все модели готовы! 🚀")

# === ПРОМПТ ДЛЯ LLM ===

SYSTEM_PROMPT = """Ты — AI-ассистент для анализа бизнес-встреч и звонков.

Твоя задача — структурировать транскрипцию в JSON формате с двумя основными разделами:

1. "discussed" - что обсуждалось на встрече (краткое саммари)
2. "tasks" - конкретные поручения с ответственными и сроками

Каждый раздел содержит 3 блока:
- "commerce" - вопросы ставок, продаж, привлечения клиентов/провайдеров
- "operations" - текущие проблемы, балансировка трафика/ликвидности, оперативные вопросы
- "technical" - интеграции, релизы, L2 поддержка

ВАЖНО:
- Для "discussed": краткие абзацы (2-4 предложения на блок)
- Для "tasks": массив объектов с полями:
  - "task": описание задачи
  - "responsible": кто ответственный (ФИО или должность)
  - "deadline": срок выполнения (если упомянут)
  - "priority": приоритет (high/medium/low) - определи сам исходя из контекста

Если в каком-то блоке ничего не обсуждалось - пиши null.
Если срок не указан - пиши "не указан".
Если ответственный не назван - пиши "не указан".

Формат ответа СТРОГО JSON без дополнительного текста:
{
  "discussed": {
    "commerce": "текст саммари или null",
    "operations": "текст саммари или null",
    "technical": "текст саммари или null"
  },
  "tasks": {
    "commerce": [
      {
        "task": "описание",
        "responsible": "ФИО",
        "deadline": "дата",
        "priority": "high"
      }
    ],
    "operations": [],
    "technical": []
  }
}
"""


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def align_speakers_with_words(diarization, words):
    """Сопоставляет слова со спикерами"""
    dialogue = []

    for word in words:
        word_start = word['start']
        word_end = word['end']
        word_mid = (word_start + word_end) / 2

        speaker_found = None
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            if turn.start <= word_mid <= turn.end:
                speaker_found = speaker
                break

        dialogue.append({
            'speaker': speaker_found or 'UNKNOWN',
            'text': word['text'],
            'start': word_start,
            'end': word_end
        })

    return dialogue


def format_dialogue_for_llm(dialogue):
    """Форматирует диалог для LLM"""
    if not dialogue:
        return ""

    # Группируем по спикерам
    grouped = []
    current_speaker = None
    current_text = []
    current_start = None

    for item in dialogue:
        if item['speaker'] != current_speaker:
            if current_speaker is not None:
                grouped.append({
                    'speaker': current_speaker,
                    'text': ' '.join(current_text),
                    'start': current_start
                })
            current_speaker = item['speaker']
            current_text = [item['text']]
            current_start = item['start']
        else:
            current_text.append(item['text'])

    if current_speaker is not None:
        grouped.append({
            'speaker': current_speaker,
            'text': ' '.join(current_text),
            'start': current_start
        })

    # Форматируем
    lines = []
    for item in grouped:
        minutes = int(item['start'] // 60)
        seconds = int(item['start'] % 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"
        lines.append(f"[{item['speaker']}, {timestamp}]: {item['text']}")

    return "\n\n".join(lines)


def download_from_s3(bucket, key, local_path):
    """Скачивает файл из S3"""
    logger.info(f"Скачивание из S3: {bucket}/{key}")
    s3_client.download_file(bucket, key, local_path)
    logger.info(f"Файл скачан в {local_path}")


def upload_to_s3(bucket, key, data):
    """Загружает JSON результат в S3"""
    logger.info(f"Загрузка результата в S3: {bucket}/{key}")
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, ensure_ascii=False, indent=2),
        ContentType='application/json',
        ServerSideEncryption='AES256'
    )
    logger.info("Результат загружен ✓")


# === ОСНОВНОЙ ОБРАБОТЧИК ===

def handler(job):
    """
    Главная функция обработки задачи.
    Вызывается RunPod serverless при получении задачи.
    """
    job_input = job['input']

    job_id = job_input['job_id']
    s3_bucket = job_input['s3_bucket']
    s3_key = job_input['s3_key']
    user_id = job_input.get('user_id')
    chat_id = job_input.get('chat_id')

    logger.info(f"Начало обработки задачи {job_id}")

    try:
        # 1. Скачиваем аудио из S3
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp_audio:
            audio_path = tmp_audio.name

        download_from_s3(s3_bucket, s3_key, audio_path)

        # 2. Транскрипция (параллельно с диаризацией)
        logger.info("Шаг 1/3: Транскрипция...")

        segments, info = whisper_model.transcribe(
            audio_path,
            language="ru",
            word_timestamps=True
        )

        # Собираем слова
        all_words = []
        for seg in segments:
            if hasattr(seg, 'words') and seg.words:
                for word in seg.words:
                    all_words.append({
                        'text': word.word,
                        'start': word.start,
                        'end': word.end
                    })

        logger.info(f"Транскрибировано {len(all_words)} слов")

        # 3. Диаризация
        logger.info("Шаг 2/3: Определение спикеров...")

        diarization = diarization_pipeline(audio_path)

        # Подсчитываем спикеров
        speakers = set()
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speakers.add(speaker)

        logger.info(f"Найдено спикеров: {len(speakers)}")

        # 4. Сопоставление спикеров с текстом
        logger.info("Шаг 2.5/3: Сопоставление спикеров...")

        dialogue = align_speakers_with_words(diarization, all_words)
        dialogue_text = format_dialogue_for_llm(dialogue)

        logger.info(f"Диалог сформирован, длина: {len(dialogue_text)} символов")

        # 5. Генерация саммари через Llama
        logger.info("Шаг 3/3: Генерация саммари...")

        prompt = f"{SYSTEM_PROMPT}\n\nТранскрипция встречи:\n\n{dialogue_text}\n\nJSON:"

        sampling_params = SamplingParams(
            temperature=0.3,
            top_p=0.9,
            max_tokens=3000
        )

        outputs = llm.generate([prompt], sampling_params)
        summary_text = outputs[0].outputs[0].text

        # Парсим JSON
        try:
            summary = json.loads(summary_text)
            logger.info("Саммари успешно создано ✓")
        except json.JSONDecodeError:
            logger.warning("Не удалось распарсить JSON от LLM, используем fallback")
            summary = {
                "error": "Failed to parse LLM output",
                "raw_output": summary_text
            }

        # 6. Формируем финальный результат
        result = {
            "job_id": job_id,
            "status": "completed",
            "full_transcript": dialogue_text,
            "discussed": summary.get("discussed"),
            "tasks": summary.get("tasks"),
            "metadata": {
                "duration": info.duration if hasattr(info, 'duration') else None,
                "language": info.language if hasattr(info, 'language') else "ru",
                "num_speakers": len(speakers),
                "num_words": len(all_words)
            }
        }

        # 7. Сохраняем результат в S3
        result_key = f"users/{user_id}/results/{job_id}.json"
        upload_to_s3(s3_bucket, result_key, result)

        # 8. Перемещаем аудио в processed
        processed_key = s3_key.replace('/new/', '/processed/')
        s3_client.copy_object(
            Bucket=s3_bucket,
            CopySource={'Bucket': s3_bucket, 'Key': s3_key},
            Key=processed_key
        )
        s3_client.delete_object(Bucket=s3_bucket, Key=s3_key)

        # 9. Отправляем callback (опционально)
        callback_url = job_input.get('callback_url')
        if callback_url and chat_id:
            try:
                logger.info(f"Отправка callback на {callback_url}")
                with httpx.Client(timeout=30.0) as client:
                    callback_response = client.post(
                        callback_url,
                        json={
                            'job_id': job_id,
                            'chat_id': chat_id,
                            'status': 'COMPLETED',
                            'result': result
                        }
                    )
                    if callback_response.status_code == 200:
                        logger.info(f"Callback отправлен успешно для job {job_id}")
                    else:
                        logger.warning(f"Callback failed: {callback_response.status_code}")
            except Exception as callback_error:
                logger.error(f"Ошибка отправки callback: {callback_error}")
                # Не падаем, результат уже в S3

        logger.info(f"Задача {job_id} завершена успешно! ✅")

        # Очистка
        os.remove(audio_path)

        return {
            "status": "success",
            "job_id": job_id,
            "result_key": result_key,
            "metadata": result["metadata"]
        }

    except Exception as e:
        logger.error(f"Ошибка обработки задачи {job_id}: {e}", exc_info=True)

        # Сохраняем ошибку в S3
        error_result = {
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        }

        result_key = f"users/{user_id}/results/{job_id}.json"
        upload_to_s3(s3_bucket, result_key, error_result)

        # Отправляем callback об ошибке
        callback_url = job_input.get('callback_url')
        if callback_url and chat_id:
            try:
                logger.info(f"Отправка error callback на {callback_url}")
                with httpx.Client(timeout=30.0) as client:
                    client.post(
                        callback_url,
                        json={
                            'job_id': job_id,
                            'chat_id': chat_id,
                            'status': 'FAILED',
                            'error': str(e)
                        }
                    )
            except Exception as callback_error:
                logger.error(f"Ошибка отправки error callback: {callback_error}")

        return {
            "status": "error",
            "job_id": job_id,
            "error": str(e)
        }


# Для RunPod serverless
runpod_handler = handler


if __name__ == "__main__":
    # Локальное тестирование
    print("Модели загружены, готов к обработке!")
    print("Для тестирования через RunPod используйте их CLI.")
