# RunPod Serverless Dockerfile для обработки аудио
# Базовый образ с CUDA
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Метаданные
LABEL maintainer="your-email@example.com"
LABEL description="Callsum ML Service - Audio transcription, diarization, and summarization"

# Отключаем интерактивные промпты
ENV DEBIAN_FRONTEND=noninteractive

# Обновляем систему и ставим зависимости
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Создаем директории для кэша моделей
RUN mkdir -p /models/whisper /models/pyannote /models/llama

# Копируем requirements
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY handler.py .

# Предзагрузка моделей для ускорения cold start
# (опционально, увеличивает размер образа но ускоряет запуск)
ARG PRELOAD_MODELS=true

RUN if [ "$PRELOAD_MODELS" = "true" ]; then \
    echo "Предзагрузка моделей..."; \
    python3 -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', device='cpu', download_root='/models/whisper')"; \
    fi

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/models
ENV TRANSFORMERS_CACHE=/models
ENV TORCH_HOME=/models

# Expose порт (для локального тестирования)
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import torch; print(torch.cuda.is_available())" || exit 1

# RunPod serverless handler
CMD ["python3", "-u", "handler.py"]
