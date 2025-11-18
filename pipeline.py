# -*- coding: utf-8 -*-
import os
import json
import torch
from dotenv import load_dotenv
from pyannote.audio import Pipeline
from faster_whisper import WhisperModel

# Загружаем переменные окружения из .env файла
load_dotenv()

# --- 1. НАСТРОЙКА И ЗАГРУЗКА МОДЕЛЕЙ ---
print("Загрузка моделей...")

# Проверка наличия токена Hugging Face
HF_TOKEN = os.getenv('HF_TOKEN')
if HF_TOKEN is None:
    raise ValueError("Не найден токен Hugging Face. Добавьте его в .env файл как переменную HF_TOKEN.")

# Определение устройства (GPU, если доступен, иначе CPU)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Загрузка модели для диаризации (определения спикеров)
try:
    diarize_pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=HF_TOKEN
    )
    diarize_pipeline.to(DEVICE)
    print(f"Модель диаризации работает на: {DEVICE}")
except Exception as e:
    print(f"Ошибка загрузки модели диаризации: {e}")
    # В реальном проекте здесь может быть более сложная обработка ошибок
    exit()


# Загрузка модели для транскрипции (распознавания речи)
# compute_type "int8" - хороший компромисс между скоростью и качеством на CPU
# compute_type "float16" - для использования на GPU
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"
transcribe_model = WhisperModel("large-v3", device=DEVICE, compute_type=COMPUTE_TYPE)
print(f"Модель транскрипции работает на: {DEVICE} с типом вычислений: {COMPUTE_TYPE}")

# Настройка клиента Ollama
# Адрес берется из переменной окружения, что позволяет гибко настраивать
# для локального запуска и для Docker.
import ollama
ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
print(f"Подключаемся к Ollama по адресу: {ollama_host}")
ollama_client = ollama.Client(host=ollama_host)


# --- 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def align_speakers_with_words(diarization, words):
    """
    Сопоставляет слова со спикерами на основе временных меток.

    Args:
        diarization: результат работы pyannote (диаризация)
        words: список словарей с ключами 'text', 'start', 'end'

    Returns:
        list: список словарей с разметкой спикеров
    """
    dialogue = []

    for word in words:
        word_start = word['start']
        word_end = word['end']
        word_mid = (word_start + word_end) / 2  # Середина слова

        # Ищем спикера для этого временного отрезка
        speaker_found = None
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            # Проверяем попадание середины слова в сегмент спикера
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
    """
    Форматирует диалог в удобный для LLM формат с группировкой по репликам.

    Args:
        dialogue: список словарей с ключами 'speaker', 'text', 'start', 'end'

    Returns:
        str: отформатированный текст диалога
    """
    if not dialogue:
        return ""

    # Группируем последовательные слова одного спикера в реплики
    grouped_dialogue = []
    current_speaker = None
    current_text = []
    current_start = None

    for item in dialogue:
        if item['speaker'] != current_speaker:
            # Сохраняем предыдущую реплику
            if current_speaker is not None:
                grouped_dialogue.append({
                    'speaker': current_speaker,
                    'text': ' '.join(current_text),
                    'start': current_start
                })

            # Начинаем новую реплику
            current_speaker = item['speaker']
            current_text = [item['text']]
            current_start = item['start']
        else:
            # Продолжаем текущую реплику
            current_text.append(item['text'])

    # Добавляем последнюю реплику
    if current_speaker is not None:
        grouped_dialogue.append({
            'speaker': current_speaker,
            'text': ' '.join(current_text),
            'start': current_start
        })

    # Форматируем в текст
    formatted_lines = []
    for i, item in enumerate(grouped_dialogue):
        timestamp = format_timestamp(item['start'])
        formatted_lines.append(f"[{item['speaker']}, {timestamp}]: {item['text']}")

    return "\n\n".join(formatted_lines)


def format_timestamp(seconds):
    """Форматирует секунды в MM:SS"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


# --- 3. ОСНОВНАЯ ФУНКЦИЯ ОБРАБОТКИ ---

def process_audio_file(audio_path: str) -> dict:
    """
    Выполняет полный цикл обработки одного аудиофайла.
    
    Args:
        audio_path (str): Путь к аудиофайлу.

    Returns:
        dict: Структурированный JSON с результатами анализа.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Аудиофайл не найден по пути: {audio_path}")

    # --- Шаг 1: Диа-ри-за-ци-я ---
    print(f"1/3: Определение спикеров (диаризация) для файла {audio_path}...")
    diarization = diarize_pipeline(audio_path)

    # --- Шаг 2: Транс-крип-ци-я ---
    print("2/3: Распознавание речи (транскрипция)...")
    segments, _ = transcribe_model.transcribe(audio_path, word_timestamps=True)

    # --- Шаг 3: Сбор-ка ди-а-ло-га ---
    print("3/3: Сборка диалога...")

    # Собираем все слова с временными метками
    all_words = []
    for seg in segments:
        if hasattr(seg, 'words') and seg.words:
            for word in seg.words:
                all_words.append({
                    'text': word.word,
                    'start': word.start,
                    'end': word.end
                })

    # Сопоставляем слова со спикерами
    dialogue = align_speakers_with_words(diarization, all_words)

    # Формируем текст с разметкой спикеров для LLM
    dialogue_text_for_llm = format_dialogue_for_llm(dialogue)
    
    
    # --- Шаг 4: Ана-лиз LLM ---
    print("Анализ диалога и структурирование по блокам...")
    
    system_prompt = (
        "Ты — AI-ассистент, который анализирует транскрипцию рабочих встреч. "
        "Твоя задача — структурировать информацию в JSON-формате по трем блокам: "
        "'technical_block', 'commercial_block' и 'other_tasks'. "
        "Для каждого блока предоставь краткое саммари и список ключевых задач. "
        "Ответ должен быть ТОЛЬКО в формате JSON."
    )
    
    try:
        response = ollama_client.generate(
            model="llama3",
            system=system_prompt,
            prompt=dialogue_text_for_llm,
            format='json'
        )
        
        structured_summary = json.loads(response['response'])
        print("Структурирование завершено.")
        return structured_summary

    except Exception as e:
        print(f"Ошибка при взаимодействии с Ollama: {e}")
        return {"error": str(e)}


# --- 3. БЛОК ДЛЯ ПРЯМОГО ЗАПУСКА И ТЕСТИРОВАНИЯ ---
if __name__ == "__main__":
    
    # Используем тестовый файл, если скрипт запущен напрямую
    TEST_AUDIO_FILE = "sample_audio.wav"
    
    print(f"\n--- ЗАПУСК В РЕЖИМЕ ТЕСТИРОВАНИЯ ДЛЯ ФАЙЛА: {TEST_AUDIO_FILE} ---")
    
    result = process_audio_file(TEST_AUDIO_FILE)
    
    # Сохраняем результат в файл
    output_filename = "structured_summary.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
        
    print("\n--- УСПЕХ! ---")
    print(f"Структурированное саммари сохранено в: {output_filename}")
    print("-----------------")
