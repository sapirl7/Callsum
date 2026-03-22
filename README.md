# 🎙️ Callsum - AI Audio Analysis Service

Облачный сервис для транскрипции, диаризации и анализа голосовых встреч с использованием AI.

![Deployment Candidate](https://img.shields.io/badge/Status-Deployment--Candidate-orange)
[![AWS](https://img.shields.io/badge/AWS-Deployed-orange)](https://aws.amazon.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 📋 Содержание

- [Особенности](#особенности)
- [Архитектура](#архитектура)
- [Стоимость](#стоимость)
- [Быстрый старт](#быстрый-старт)
- [Деплой](#деплой)
- [Использование](#использование)
- [Мониторинг](#мониторинг)
- [Troubleshooting](#troubleshooting)

## ✨ Особенности

### 🎯 Основной функционал
- **Транскрипция** - Whisper large-v3 для точного распознавания речи (русский язык)
- **Диаризация** - Pyannote 3.1 для определения спикеров
- **AI Анализ** - Llama 3.1 8B Instruct для генерации структурированных саммари
- **Telegram Bot** - Удобный интерфейс для загрузки аудио

### 🏗️ Операционные возможности
- ✅ **Rate Limiting** - защита от злоупотреблений (10 req/hour, 50 req/day)
- ✅ **Presigned URLs** - безопасная работа с S3 без передачи credentials
- ✅ **Progress Updates** - real-time уведомления о ходе обработки
- ✅ **Graceful Degradation** - возврат транскрипции даже при сбое LLM
- ✅ **S3 Versioning** - защита от потери данных
- ✅ **DynamoDB PITR** - point-in-time recovery для метаданных
- ✅ **Budget Alarms** - контроль расходов с алертами
- ✅ **Health Check** - endpoint для мониторинга
- ✅ **CloudWatch Dashboard** - единый дашборд всех метрик
- ✅ **SNS Alerts** - email уведомления при проблемах

### 📊 Структура саммари

```json
{
  "discussed": {
    "commerce": "Обсуждение ставок, продаж, клиентов...",
    "operations": "Текущие проблемы, балансировка трафика...",
    "technical": "Интеграции, релизы, L2..."
  },
  "tasks": {
    "commerce": [
      {
        "task": "Увеличить ставки на 5%",
        "responsible": "Иван Петров",
        "deadline": "до конца недели",
        "priority": "high"
      }
    ],
    "operations": [...],
    "technical": [...]
  }
}
```

## 🏛️ Архитектура

```
┌─────────────┐
│   Telegram  │
│     Bot     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│         AWS Lambda (Bot)            │
│  ┌─────────────────────────────┐   │
│  │ • Rate Limiting             │   │
│  │ • Presigned URLs Generation │   │
│  │ • S3 Upload (encrypted)     │   │
│  │ • DynamoDB Write            │   │
│  │ • RunPod Trigger            │   │
│  └─────────────────────────────┘   │
└──────┬──────────────────────┬───────┘
       │                      │
       ▼                      ▼
┌─────────────┐      ┌────────────────┐
│  S3 Bucket  │      │    DynamoDB    │
│  (AES-256)  │      │ • Jobs         │
│             │      │ • Rate Limits  │
└─────────────┘      └────────────────┘
       │
       │ presigned URL
       ▼
┌────────────────────────────────────┐
│    RunPod Serverless (GPU)         │
│  ┌─────────────────────────────┐  │
│  │ 1. Download via presigned   │  │
│  │ 2. Whisper (transcribe)     │  │
│  │ 3. Pyannote (diarization)   │  │
│  │ 4. Llama 3 (summarize)      │  │
│  │ 5. Upload via presigned     │  │
│  │ 6. Send progress callbacks  │  │
│  └─────────────────────────────┘  │
└────────────────────────────────────┘
       │
       │ callback
       ▼
┌─────────────────────────────────────┐
│         AWS Lambda (Bot)            │
│  • Process callback                 │
│  • Send results to user             │
│  • Update DynamoDB                  │
└─────────────────────────────────────┘
```

### Компоненты:
- **Telegram Bot (AWS Lambda)** - прием аудио, управление задачами
- **RunPod Serverless** - ML обработка (Whisper + Pyannote + Llama)
- **S3** - хранение аудио и результатов (encrypted, versioned)
- **DynamoDB** - метаданные задач и rate limiting
- **API Gateway** - webhook endpoint + health check
- **CloudWatch** - логи, метрики, алармы
- **SNS** - уведомления об алармах
- **AWS Budgets** - контроль расходов

## 💰 Стоимость

### Ожидаемые расходы (при 100 запросах/месяц):

| Сервис | Стоимость/месяц |
|--------|----------------|
| **AWS Lambda** | $0.20 |
| **S3** | $0.50 |
| **DynamoDB** | $0.25 |
| **API Gateway** | $0.35 |
| **CloudWatch** | $0.30 |
| **Secrets Manager** | $1.20 |
| **RunPod GPU** (RTX 3090) | $0.44/hour × 30 hours ≈ $13.20 |
| **ИТОГО** | **~$16/месяц** |

### Оптимизация расходов:
- ✅ Serverless GPU (платим только за использование)
- ✅ S3 Lifecycle (автоудаление старых файлов)
- ✅ DynamoDB TTL (автоудаление записей)
- ✅ Budget Alerts (контроль перерасхода)

## 🚀 Быстрый старт

### Предварительные требования:
- AWS аккаунт
- Terraform >= 1.0
- AWS CLI
- Docker (для RunPod)
- Python 3.10+

### 1. Клонирование репозитория
```bash
git clone https://github.com/yourusername/callsum.git
cd callsum
```

### 2. Настройка переменных
```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Отредактируйте terraform.tfvars и заполните все значения
```

### 3. Валидация конфигурации
```bash
cd ../../deployment
./validate_deployment.sh
```

### 4. Деплой
```bash
# Деплой AWS инфраструктуры
./deploy_aws.sh

# Деплой RunPod ML сервиса
./deploy_runpod.sh
```

## 📦 Деплой

### Детальная инструкция деплоя AWS:

```bash
cd infrastructure/terraform

# 1. Инициализация
terraform init

# 2. Проверка плана
terraform plan

# 3. Применение
terraform apply

# 4. Получение outputs
terraform output -json > outputs.json

# 5. Настройка Telegram webhook
WEBHOOK_URL=$(terraform output -raw api_gateway_url)
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
     -H "Content-Type: application/json" \
     -d "{\"url\": \"${WEBHOOK_URL}\"}"
```

### Деплой RunPod сервиса:

```bash
cd runpod_service

# 1. Build Docker image
docker build -t callsum-ml:latest .

# 2. Push to Docker Hub или Registry
docker tag callsum-ml:latest yourusername/callsum-ml:latest
docker push yourusername/callsum-ml:latest

# 3. Создание RunPod endpoint через UI или CLI
# Используйте образ: yourusername/callsum-ml:latest
# GPU: RTX 3090 или A40
# Serverless: Enabled
```

## 📱 Использование

### Через Telegram Bot:

1. Найдите своего бота в Telegram
2. Отправьте команду `/start`
3. Отправьте голосовое сообщение или аудио файл
4. Дождитесь результата (получите уведомления о прогрессе)

### Поддерживаемые форматы:
- Voice Messages (.ogg)
- MP3 (.mp3)
- WAV (.wav)
- M4A (.m4a)
- WebM (.webm)

### Лимиты:
- Максимальная длительность: 2 часа
- Максимальный размер: 100 MB
- Rate limit: 10 запросов/час, 50 запросов/день

## 📊 Мониторинг

### CloudWatch Dashboard:
```
URL: https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#dashboards:name=callsum-dashboard-prod
```

### Health Check:
```bash
curl https://your-api-gateway-url/health
```

Ответ:
```json
{
  "status": "healthy",
  "service": "callsum-api",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

### Основные метрики:
- **Lambda Invocations** - количество вызовов
- **Lambda Errors** - ошибки
- **Lambda Duration** - время выполнения
- **DynamoDB Capacity** - использование capacity units
- **S3 Storage** - количество объектов и размер
- **API Gateway Requests** - запросы к API
- **RunPod Job Success Rate** - успешность GPU задач

### Алармы:
- 📧 Email уведомления при превышении порогов
- 💰 Budget alerts при превышении 50%, 80%, 100%
- 🔥 Lambda errors (> 5 за 5 минут)
- ⏱️ Lambda duration (> 50 секунд)

## 🔧 Troubleshooting

### Проблема: "Rate limit exceeded"
**Решение**: Пользователь превысил лимит (10/час или 50/день). Подождите или увеличьте лимиты в `variables.tf`.

### Проблема: "Processing failed"
**Решение**: 
1. Проверьте CloudWatch Logs: `/aws/lambda/callsum-telegram-bot-prod`
2. Проверьте RunPod logs
3. Проверьте DynamoDB запись задачи

### Проблема: "No results received"
**Решение**: 
1. Проверьте что callback URL настроен в Lambda
2. Проверьте RunPod endpoint доступность
3. Проверьте S3 presigned URL expiration (1 час)

### Проблема: Budget alert triggered
**Решение**: 
1. Проверьте Cost Explorer в AWS Console
2. Проверьте количество RunPod hours
3. Включите более агрессивный rate limiting

## 📚 Документация

- [Documentation Map](docs/README.md) - каноническая карта документации
- [Handoff Checklist](docs/HANDOFF_CHECKLIST.md) - финальный чеклист передачи заказчику
- [Project Status](docs/PROJECT_STATUS.md) - что проверено локально и что ещё нужно проверить на staging
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Детальное руководство по деплою
- [Architecture](docs/ARCHITECTURE.md) - Подробная архитектура
- [API Reference](docs/API.md) - API документация
- [Configuration](docs/CONFIGURATION.md) - Конфигурационные параметры

## 🤝 Contributing

Pull requests приветствуются! Для больших изменений сначала откройте issue.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- [Whisper](https://github.com/openai/whisper) by OpenAI
- [Pyannote](https://github.com/pyannote/pyannote-audio) 
- [Llama 3](https://ai.meta.com/llama/) by Meta
- [RunPod](https://runpod.io) for GPU infrastructure

---

Made with ❤️ for efficient meeting analysis
