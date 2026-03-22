# 🚀 CALLSUM - Deployment Guide

> Статус: расширенный обзорный гайд.
> Канонические handoff-материалы: `docs/HANDOFF_CHECKLIST.md`, `docs/PROJECT_STATUS.md`, `docs/DEPLOYMENT_GUIDE.md`.

**Secure, Scalable Call Transcription & Summarization System**

Автоматическая обработка звонков с транскрипцией, диаризацией и структурированным саммари.

## ✨ Возможности

- 🎯 **Транскрипция** - Whisper large-v3 (русский язык)
- 👥 **Диаризация** - определение спикеров (Pyannote 3.1)
- 📋 **Структурированное саммари** - Llama 3.1 8B
  - Блок "Коммерция"
  - Блок "Операционка"
  - Блок "Техника"
  - Поручения с ответственными и сроками
- 📱 **Telegram интеграция** - просто отправьте голосовое
- 🔒 **Полная безопасность** - шифрование, изоляция, минимальные права
- 💰 **Экономично** - ~$10-15/месяц при 60 часах аудио

---

## 📁 Структура проекта

```
Callsum/
├── requirements.txt            # Dev/test зависимости
│
├── telegram_bot/               # Telegram бот (AWS Lambda)
│   ├── bot.py                  # Lambda handler
│   ├── bot_local.py            # Локальное тестирование
│   └── requirements.txt
│
├── runpod_service/             # ML сервис (RunPod GPU)
│   ├── handler.py              # RunPod serverless handler
│   ├── Dockerfile              # Docker образ
│   └── requirements.txt
│
├── infrastructure/             # Terraform (AWS)
│   └── terraform/
│       ├── main.tf             # Основная конфигурация
│       ├── variables.tf        # Переменные
│       ├── s3.tf               # S3 bucket
│       ├── dynamodb.tf         # DynamoDB таблица
│       ├── lambda.tf           # Lambda функция
│       ├── api_gateway.tf      # API Gateway
│       ├── iam.tf              # IAM роли
│       ├── secrets.tf          # Secrets Manager
│       ├── outputs.tf          # Outputs
│       └── terraform.tfvars.example  # Шаблон конфигурации
│
├── deployment/                 # Deployment скрипты
│   ├── deploy_aws.sh           # Деплой AWS (автоматизация)
│   └── deploy_runpod.sh        # Деплой RunPod
│
└── docs/                       # Документация
    └── DEPLOYMENT_GUIDE.md     # Полное руководство
```

---

## 🎯 Быстрый старт

### 1. Предварительные требования

- AWS аккаунт
- RunPod аккаунт ($10 минимум)
- Hugging Face токен
- Telegram Bot токен
- Docker, Terraform, AWS CLI

### 2. Клонируйте и настройте

```bash
git clone <repository-url>
cd Callsum

# Настройте Terraform переменные
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Заполните своими токенами
```

### 3. Деплой AWS

```bash
cd ../../deployment
./deploy_aws.sh
```

### 4. Деплой RunPod

```bash
./deploy_runpod.sh
```

### 5. Установите Telegram Webhook

```bash
# Получите webhook URL
cd ../infrastructure/terraform
WEBHOOK_URL=$(terraform output -raw api_gateway_url)

# Установите webhook
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$WEBHOOK_URL\"}"
```

### 6. Готово! 🎉

Отправьте голосовое сообщение боту в Telegram.

---

## 📖 Полная документация

См. [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) для детальных инструкций.

---

## 💰 Стоимость

### AWS (~$1-3/месяц):
- S3: ~$1
- Lambda: ~$0.50
- DynamoDB: ~$0.30
- API Gateway: ~$0.10

### RunPod (~$8-11/месяц при 60 часах аудио):
- RTX 3090: $0.44/час
- ~18-20 часов GPU времени/месяц
- Платите только за использование (serverless)

**ИТОГО: ~$10-15/месяц**

---

## 🏗️ Архитектура

```
┌─────────────┐
│  Telegram   │
│    User     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│           AWS CLOUD                 │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────┐    ┌──────────┐     │
│  │    API   │───►│  Lambda  │     │
│  │  Gateway │    │   (Bot)  │     │
│  └──────────┘    └─────┬────┘     │
│                        │           │
│  ┌────┐  ┌────┐  ┌────┴────┐     │
│  │ S3 │    │DynamoDB │     │
│  └────┘  └─┬──┘  └─────────┘     │
│            │                       │
└────────────┼───────────────────────┘
             │
             ▼
    ┌────────────────────┐
    │  RunPod GPU Cloud  │
    │  ┌──────────────┐  │
    │  │ Whisper STT  │  │
    │  │ Pyannote     │  │
    │  │ Llama 3.1 8B │  │
    │  └──────────────┘  │
    └────────────────────┘
```

**Поток данных:**
1. Пользователь отправляет голосовое → Telegram API
2. Webhook → API Gateway → Lambda
3. Lambda загружает в S3 → триггерит RunPod
4. Lambda триггерит RunPod Serverless
5. RunPod обрабатывает (Whisper + Pyannote + Llama)
6. Результат сохраняется в S3
7. Бот отправляет саммари пользователю

---

## 🔒 Безопасность

- ✅ **Шифрование at-rest**: S3 (AES-256), DynamoDB
- ✅ **Шифрование in-transit**: HTTPS везде
- ✅ **Изоляция пользователей**: S3 структура по user_id
- ✅ **Минимальные права**: IAM Least Privilege
- ✅ **Secrets Management**: AWS Secrets Manager
- ✅ **Аудит**: CloudWatch Logs
- ✅ **Автоудаление**: S3 Lifecycle (30 дней)

---

## 📊 Мониторинг

### CloudWatch Dashboards
- Lambda errors & duration
- API Gateway requests
- RunPod job success rate
- DynamoDB throttles

### RunPod Analytics
- Execution time
- Cold starts
- GPU utilization
- Costs

---

## 🛠️ Troubleshooting

### Бот не отвечает
```bash
# Проверьте webhook
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Проверьте логи
aws logs tail /aws/lambda/callsum-telegram-bot-prod --follow
```

### RunPod не запускается
```bash
# Тест Docker образа
docker run --gpus all callsum/ml-service:latest

# Проверьте логи в RunPod Console
```

### Полный список решений
См. [docs/DEPLOYMENT_GUIDE.md#troubleshooting](docs/DEPLOYMENT_GUIDE.md#troubleshooting)

---

## 📝 Changelog

### v2.0.0 (Deployment Candidate)
- ✅ Telegram бот (AWS Lambda)
- ✅ RunPod Serverless интеграция
- ✅ Terraform IaC
- ✅ Кастомная структура саммари
- ✅ Полная безопасность
- ✅ Автоматизированный деплой

### v1.0.0 (MVP)
- ✅ Локальная обработка
- ✅ Whisper + Pyannote + Ollama
- ✅ Базовое саммари

---

## 👥 Contributing

Pull requests welcome! См. [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 License

MIT License - см. [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

- [Faster Whisper](https://github.com/guillaumekln/faster-whisper)
- [Pyannote Audio](https://github.com/pyannote/pyannote-audio)
- [vLLM](https://github.com/vllm-project/vllm)
- [RunPod](https://www.runpod.io/)

---

**Сделано с ❤️ для автоматизации обработки звонков**
