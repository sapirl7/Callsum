# ⚡ Callsum - Быстрый Старт

> Статус: вспомогательный quick-start.
> Канонические handoff-материалы: `docs/HANDOFF_CHECKLIST.md`, `docs/PROJECT_STATUS.md`, `docs/DEPLOYMENT_GUIDE.md`.

## 🎯 Что это?

**Callsum** - AI-сервис для автоматической обработки аудио встреч:
- 🎙️ Транскрипция (Whisper large-v3)
- 👥 Определение спикеров (Pyannote 3.1)
- 📝 Умное саммари (Llama 3.1-8B)
- 📱 Telegram бот интерфейс

---

## 💰 Стоимость

### Вариант 1: AWS S3 (полная AWS инфраструктура)
- **AWS:** ~$2-5/месяц (Lambda, DynamoDB, S3, API Gateway)
- **RunPod:** ~$10-15/месяц (GPU обработка)
- **ИТОГО:** **$12-20/месяц**

### Вариант 2: DigitalOcean Spaces + AWS
- **AWS:** ~$2-3/месяц (Lambda, DynamoDB, API Gateway)
- **DO Spaces:** $5/месяц (хранилище)
- **RunPod:** ~$10-15/месяц (GPU обработка)
- **ИТОГО:** **$17-23/месяц** (но проще управлять)

---

## 🚀 Быстрый старт (30 минут)

### 1. Создайте аккаунты

| Сервис | Зачем | Ссылка | Стоимость |
|--------|-------|--------|-----------|
| **AWS** | Бот + БД | [aws.amazon.com](https://aws.amazon.com) | ~$2/месяц |
| **RunPod** | GPU обработка | [runpod.io](https://runpod.io) | ~$10-15/месяц |
| **Telegram** | Бот интерфейс | [@BotFather](https://t.me/BotFather) | Бесплатно |
| **Hugging Face** | ML модели | [huggingface.co](https://huggingface.co) | Бесплатно |

**Опционально:**
| **DigitalOcean** | Хранилище | [digitalocean.com](https://digitalocean.com) | $5/месяц |

---

### 2. Получите токены

```bash
# 1. Telegram Bot Token
# Telegram → @BotFather → /newbot

# 2. Hugging Face Token
# huggingface.co → Settings → Access Tokens → New (Read)

# 3. AWS Access Keys
# AWS Console → IAM → Users → Security credentials → Create access key

# 4. RunPod API Key
# runpod.io → Settings → API Keys → Create

# Опционально: DigitalOcean Spaces Keys
# digitalocean.com → API → Spaces Keys → Generate New Key
```

---

### 3. Установите инструменты

```bash
# Terraform
brew install terraform  # macOS
# или https://developer.hashicorp.com/terraform/downloads

# Docker
# Скачайте с https://www.docker.com/products/docker-desktop/

# AWS CLI
brew install awscli  # macOS
# или https://aws.amazon.com/cli/

# Настройте AWS CLI
aws configure
# Введите Access Key ID и Secret Access Key
```

---

### 4. Настройте проект

```bash
# Клонируйте репозиторий
git clone <ваш-репозиторий>
cd Callsum

# Скопируйте конфиг
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars

# Отредактируйте terraform.tfvars
nano terraform.tfvars  # или используйте VS Code
```

**Минимальные обязательные параметры:**
```hcl
# Telegram
telegram_bot_token = "1234567890:ABC..."
telegram_secret_token = "$(openssl rand -hex 32)"

# Hugging Face
hf_token = "hf_ABC..."

# RunPod (заполните после создания endpoint)
runpod_api_key = "TEMP"
runpod_endpoint_url = "https://api.runpod.ai/v2/TEMP"

# S3 Bucket
s3_bucket_name = "callsum-prod-<ваши-инициалы>"

# AWS
aws_region = "us-east-1"
```

---

### 5. Деплой AWS инфраструктуры

```bash
# Инициализация
terraform init

# Проверка
terraform plan

# Деплой (займет ~5-7 минут)
terraform apply
# Введите: yes

# Сохраните webhook URL из outputs
```

---

### 6. Деплой ML сервиса на RunPod

```bash
# Вернитесь в корень проекта
cd ../../runpod_service

# Экспортируйте HF Token
export HF_TOKEN=hf_ваш_токен

# Соберите Docker образ (~30-40 минут)
docker build \
  --build-arg PRELOAD_MODELS=true \
  --build-arg HF_TOKEN=$HF_TOKEN \
  -t callsum-ml:latest \
  .

# Залогиньтесь в Docker Hub
docker login

# Загрузите образ (~20-30 минут)
docker tag callsum-ml:latest <ваш-username>/callsum-ml:latest
docker push <ваш-username>/callsum-ml:latest
```

**Создайте RunPod Endpoint:**
1. https://runpod.io/console/serverless → New Endpoint
2. **Name:** `callsum-ml-service`
3. **GPU:** RTX 3090 или RTX 4090
4. **Docker Image:** `<ваш-username>/callsum-ml:latest`
5. **Min Workers:** 0
6. **Max Workers:** 1
7. **Environment Variables:**
   ```
   HF_TOKEN=hf_ваш_токен
   ```

**Обновите Terraform:**
```bash
cd ../infrastructure/terraform
nano terraform.tfvars
# Обновите runpod_api_key и runpod_endpoint_url
terraform apply
```

---

### 7. Настройте Telegram Webhook

```bash
# Получите webhook URL
terraform output -json | jq -r '.summary.value.webhook_url'

# Установите webhook
curl -X POST "https://api.telegram.org/bot<ваш-токен>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "<webhook-url>",
    "secret_token": "<ваш-secret-token>"
  }'

# Проверьте
curl "https://api.telegram.org/bot<ваш-токен>/getWebhookInfo"
```

---

### 8. Тестируйте!

1. Найдите бота в Telegram по username
2. Отправьте `/start`
3. Запишите голосовое сообщение (30-60 сек)
4. Отправьте боту
5. Ждите результат (~2-3 минуты)

---

## 📚 Подробные руководства

- **[DEPLOYMENT_GUIDE_FULL.md](DEPLOYMENT_GUIDE_FULL.md)** - Полное пошаговое руководство
- **[docs/DIGITALOCEAN_SPACES_GUIDE.md](docs/DIGITALOCEAN_SPACES_GUIDE.md)** - Использование DO Spaces
- **[README.md](README.md)** - Обзор проекта и архитектуры

---

## 🛠 Troubleshooting

### Бот не отвечает

```bash
# Проверьте логи Lambda
aws logs tail /aws/lambda/callsum-lambda-telegram-bot-prod --follow

# Проверьте webhook
curl "https://api.telegram.org/bot<токен>/getWebhookInfo"
```

### GPU timeout

Увеличьте timeout в `terraform.tfvars`:
```hcl
RUNPOD_TIMEOUT_SECONDS = 7200  # 2 часа
```

### Out of memory в RunPod

Переключитесь на RTX 4090 в RunPod Endpoint Settings.

---

## 💡 Полезные команды

```bash
# Проверка логов
aws logs tail /aws/lambda/callsum-lambda-telegram-bot-prod --follow

# Пересборка Lambda package
./deployment/build_lambda_package.sh

# Применение обновленного артефакта
cd infrastructure/terraform
terraform apply

# Проверка стоимости
# AWS Console → Cost Explorer

# Удаление всего проекта
cd infrastructure/terraform
terraform destroy
```

---

## 📞 Поддержка

**Проблемы с деплоем?**
1. Проверьте секцию Troubleshooting в DEPLOYMENT_GUIDE_FULL.md
2. Проверьте CloudWatch Logs
3. Проверьте RunPod Logs

**Документация:**
- AWS Lambda: https://docs.aws.amazon.com/lambda/
- RunPod: https://docs.runpod.io/
- Terraform: https://developer.hashicorp.com/terraform/docs

---

## ✅ Checklist

- [ ] Все аккаунты созданы
- [ ] Все токены получены и сохранены
- [ ] Инструменты установлены (Terraform, Docker, AWS CLI)
- [ ] `terraform.tfvars` настроен
- [ ] AWS инфраструктура задеплоена (`terraform apply`)
- [ ] Docker образ собран и загружен
- [ ] RunPod Endpoint создан и настроен
- [ ] Terraform обновлен с RunPod credentials
- [ ] Telegram webhook установлен
- [ ] Бот протестирован и работает

---

🎉 **Поздравляем! Ваш Callsum бот готов к использованию!**
