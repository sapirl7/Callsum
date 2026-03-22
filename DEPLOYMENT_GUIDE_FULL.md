# 🚀 Полное руководство по деплою Callsum

> Статус: подробный расширенный гайд.
> Для handoff и финальной приёмки используйте `docs/HANDOFF_CHECKLIST.md` и `docs/PROJECT_STATUS.md`.

## Обзор архитектуры

**Callsum** использует гибридную cloud-архитектуру:
- **AWS** - Telegram бот, хранилище, база данных (легкие операции)
- **RunPod** - ML обработка на GPU (тяжелые вычисления)

### Что вам понадобится:

1. **AWS аккаунт** (~$2-5/месяц)
2. **RunPod аккаунт** (~$10-15/месяц при активном использовании)
3. **Telegram Bot Token** (бесплатно)
4. **Hugging Face Token** (бесплатно)
5. **Docker Desktop** (для сборки образа)
6. **Terraform** (для автоматического деплоя)

---

## 📋 ЧАСТЬ 1: Подготовка (30 минут)

### 1.1 Создание AWS аккаунта

1. Перейдите на https://aws.amazon.com
2. Нажмите **Create an AWS Account**
3. Заполните данные:
   - Email
   - Пароль
   - Имя аккаунта (например: "callsum-production")
4. Привяжите банковскую карту (списание $1 для проверки)
5. Выберите **Free Tier** план

**💰 Стоимость:** Первые 12 месяцев большинство сервисов бесплатны (Free Tier).

---

### 1.2 Установка AWS CLI

**macOS:**
```bash
brew install awscli
```

**Linux:**
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows:**
Скачайте установщик: https://aws.amazon.com/cli/

**Проверка:**
```bash
aws --version
# Должно показать: aws-cli/2.x.x
```

---

### 1.3 Создание AWS Access Keys

1. Войдите в AWS Console: https://console.aws.amazon.com
2. В правом верхнем углу нажмите на своё имя → **Security credentials**
3. Прокрутите до **Access keys** → **Create access key**
4. Выберите **Command Line Interface (CLI)**
5. Сохраните:
   - `Access key ID` (например: AKIAIOSFODNN7EXAMPLE)
   - `Secret access key` (например: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY)

**⚠️ ВАЖНО:** Secret key показывается только один раз! Сохраните в надежное место.

**Настройка локально:**
```bash
aws configure
# AWS Access Key ID: <вставьте ваш ключ>
# AWS Secret Access Key: <вставьте ваш secret>
# Default region: us-east-1
# Default output format: json
```

---

### 1.4 Создание Telegram бота

1. Откройте Telegram
2. Найдите бота **@BotFather**
3. Отправьте команду `/newbot`
4. Введите имя бота (например: "Callsum Audio Analyzer")
5. Введите username (например: "callsum_audio_bot")
6. **Сохраните токен** (например: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

**Дополнительные настройки:**
```
/setdescription - Опишите функции бота
/setabouttext - Краткое описание
/setuserpic - Загрузите аватар
```

---

### 1.5 Получение Hugging Face Token

1. Перейдите на https://huggingface.co
2. Зарегистрируйтесь / войдите
3. Перейдите в **Settings** → **Access Tokens**
4. Нажмите **New token**
5. Выберите тип: **Read**
6. Назовите: "callsum-pyannote"
7. **Сохраните токен** (например: `hf_AbCdEfGhIjKlMnOpQrStUvWxYz`)

---

### 1.6 Регистрация на RunPod

1. Перейдите на https://www.runpod.io
2. Нажмите **Sign Up**
3. Используйте Google или Email
4. **Пополните баланс** минимум на $10:
   - Community Cloud: от $0.20/час (RTX 3090)
   - Secure Cloud: от $0.44/час (RTX 3090)

**Рекомендация:** Начните с $10-20 для тестов.

---

### 1.7 Установка Terraform

**macOS:**
```bash
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

**Linux:**
```bash
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

**Windows:**
Скачайте: https://developer.hashicorp.com/terraform/downloads

**Проверка:**
```bash
terraform --version
# Должно показать: Terraform v1.x.x
```

---

### 1.8 Установка Docker Desktop

**macOS/Windows:**
Скачайте с https://www.docker.com/products/docker-desktop/

**Linux:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**Проверка:**
```bash
docker --version
# Docker version 24.x.x
```

---

## 📦 ЧАСТЬ 2: Деплой AWS инфраструктуры (20 минут)

### 2.1 Клонирование проекта

```bash
git clone <ваш-репозиторий-url>
cd Callsum
```

---

### 2.2 Настройка Terraform переменных

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

**Отредактируйте `terraform.tfvars`:**
```bash
nano terraform.tfvars  # или используйте VS Code
```

**Заполните все значения:**
```hcl
# === AWS REGION ===
aws_region = "us-east-1"  # Или ваш регион (eu-west-1, ap-southeast-1)
environment = "prod"

# === TELEGRAM ===
telegram_bot_token = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # От @BotFather

# ВАЖНО: Сгенерируйте случайный токен для безопасности webhook
# Выполните: openssl rand -hex 32
telegram_secret_token = "ваш_случайный_64_символьный_токен"

# === HUGGING FACE ===
hf_token = "hf_AbCdEfGhIjKlMnOpQrStUvWxYz"  # От huggingface.co

# === RUNPOD (заполним позже) ===
runpod_api_key = "TEMPORARY_WILL_UPDATE_LATER"
runpod_endpoint_url = "https://api.runpod.ai/v2/TEMPORARY"

# === NAMING ===
s3_bucket_name = "callsum-prod-<ваши-инициалы>"  # Должно быть уникально!

# === БЮДЖЕТ (опционально) ===
alert_email = "ваш@email.com"  # Для уведомлений о расходах
monthly_budget_limit = 25  # USD
runpod_monthly_limit = 15  # USD
```

---

### 2.3 Генерация Secret Token для Telegram

```bash
openssl rand -hex 32
```

Скопируйте результат в `telegram_secret_token` в `terraform.tfvars`.

---

### 2.4 Инициализация Terraform

```bash
terraform init
```

**Вывод должен быть:**
```
Terraform has been successfully initialized!
```

---

### 2.5 Проверка плана

```bash
terraform plan
```

**Проверьте что будет создано:**
- ✅ S3 Bucket (хранилище)
- ✅ DynamoDB Tables (база данных)
- ✅ Lambda Function (бот)
- ✅ API Gateway (webhook)
- ✅ Secrets Manager (токены)
- ✅ CloudWatch Dashboard (мониторинг)
- ✅ Budget Alarms (контроль расходов)

**НЕ должно быть:**
- ❌ SQS Queue (мы удалили)

---

### 2.6 Деплой инфраструктуры

```bash
terraform apply
```

Введите `yes` когда будет запрос подтверждения.

**⏱ Время деплоя:** ~5-7 минут

**После успешного деплоя увидите:**
```
Apply complete! Resources: 15 added, 0 changed, 0 destroyed.

Outputs:

summary = {
  "webhook_url" = "https://abc123xyz.execute-api.us-east-1.amazonaws.com/prod/webhook"
  "s3_bucket" = "callsum-prod-..."
  ...
}
```

**💾 Сохраните:**
- `webhook_url` - понадобится для настройки Telegram webhook

---

### 2.7 Упаковка Lambda кода

```bash
./deployment/build_lambda_package.sh

cd infrastructure/terraform
terraform apply
```

---

## 🐳 ЧАСТЬ 3: Деплой ML сервиса на RunPod (30 минут)

### 3.1 Создание RunPod Serverless Endpoint

1. Войдите на https://www.runpod.io/console/serverless
2. Нажмите **+ New Endpoint**
3. Заполните:
   - **Name:** `callsum-ml-service`
   - **GPU Type:** RTX 3090 (24GB VRAM) или RTX 4090
   - **Min Workers:** 0 (serverless - экономия)
   - **Max Workers:** 1 (для начала)
   - **Container Disk:** 20 GB
   - **Docker Image:** `<оставьте пустым, заполним позже>`

4. **Environment Variables:**
   ```
   HF_TOKEN=hf_AbCdEfGhIjKlMnOpQrStUvWxYz
   ```

5. Нажмите **Create**

6. **Сохраните:**
   - **Endpoint ID** (например: `abc123xyz456`)
   - **API Key** (в разделе API Keys)

**Ваш Endpoint URL будет:**
```
https://api.runpod.ai/v2/<endpoint-id>/runsync
```

---

### 3.2 Сборка Docker образа

```bash
cd ../runpod_service
export HF_TOKEN=hf_AbCdEfGhIjKlMnOpQrStUvWxYz  # Ваш токен
```

**Соберите образ:**
```bash
docker build \
  --build-arg PRELOAD_MODELS=true \
  --build-arg HF_TOKEN=$HF_TOKEN \
  -t callsum-ml:latest \
  .
```

**⏱ Время сборки:** ~30-40 минут (загружаются модели Whisper + Llama 3.1)

**💾 Размер образа:** ~15-20 GB

---

### 3.3 Пуш образа в Docker Hub

**Создайте аккаунт на Docker Hub:**
1. https://hub.docker.com → Sign Up
2. Создайте репозиторий: `callsum-ml`

**Залогиньтесь:**
```bash
docker login
# Username: <ваш-username>
# Password: <ваш-пароль>
```

**Тегируйте и запушьте:**
```bash
docker tag callsum-ml:latest <ваш-username>/callsum-ml:latest
docker push <ваш-username>/callsum-ml:latest
```

**⏱ Время загрузки:** ~20-30 минут (зависит от скорости интернета)

---

### 3.4 Обновление RunPod Endpoint

1. Вернитесь в RunPod Console
2. Откройте ваш Endpoint → **Settings**
3. **Docker Image:** `<ваш-username>/callsum-ml:latest`
4. Нажмите **Save**

**Тестирование:**
```bash
curl -X POST "https://api.runpod.ai/v2/<endpoint-id>/runsync" \
  -H "Authorization: Bearer <ваш-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "test": true
    }
  }'
```

**Ожидаемый результат:** Статус 200, контейнер запустился

---

### 3.5 Обновление Terraform с RunPod credentials

```bash
cd ../../infrastructure/terraform
nano terraform.tfvars
```

**Обновите строки:**
```hcl
runpod_api_key = "ваш-runpod-api-key"
runpod_endpoint_url = "https://api.runpod.ai/v2/<endpoint-id>/runsync"
```

**Примените изменения:**
```bash
terraform apply
```

---

## 🔗 ЧАСТЬ 4: Настройка Telegram Webhook (5 минут)

### 4.1 Установка webhook

**Получите webhook URL из Terraform:**
```bash
terraform output -json | jq -r '.summary.value.webhook_url'
```

**Установите webhook:**
```bash
curl -X POST "https://api.telegram.org/bot<ваш-бот-токен>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "<ваш-webhook-url>",
    "secret_token": "<ваш-secret-token-из-tfvars>"
  }'
```

**Проверьте:**
```bash
curl "https://api.telegram.org/bot<ваш-бот-токен>/getWebhookInfo"
```

**Ожидаемый результат:**
```json
{
  "ok": true,
  "result": {
    "url": "https://abc123.execute-api.us-east-1.amazonaws.com/prod/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "last_error_date": 0
  }
}
```

---

## ✅ ЧАСТЬ 5: Тестирование (10 минут)

### 5.1 Первый тест

1. Откройте Telegram
2. Найдите вашего бота по username
3. Отправьте `/start`

**Ожидаемый ответ:**
```
🎙️ Привет! Я Callsum.

Отправь мне голосовое сообщение или аудиофайл,
и я создам подробный анализ встречи.
```

---

### 5.2 Отправка тестового аудио

1. Запишите голосовое сообщение (30-60 секунд)
2. Отправьте боту

**Ожидаемое поведение:**
```
✅ Аудио получено!
📊 Длительность: 45 секунд
🔄 Начинаю обработку...

---

🚀 Задача запущена!

GPU сервер пробудился и начал обработку.
Статус будет обновляться в этом сообщении... ⏳
```

**Прогресс updates (то же сообщение редактируется):**
```
🚀 Задача запущена!

⏳ Транскрибирую аудио...
Прогресс: 20%
```

**После завершения (~2-3 минуты для 1 минуты аудио):**
```
✅ ОБРАБОТКА ЗАВЕРШЕНА

📋 ЧТО ОБСУДИЛИ:
...
📌 ПОРУЧЕНИЯ:
...
```

---

### 5.3 Проверка логов

**CloudWatch Logs:**
```bash
aws logs tail /aws/lambda/callsum-lambda-telegram-bot-prod --follow
```

**RunPod Logs:**
1. RunPod Console → Endpoints → Ваш endpoint → Logs
2. Проверьте последние запросы

---

## 📊 ЧАСТЬ 6: Мониторинг и управление

### 6.1 CloudWatch Dashboard

1. AWS Console → CloudWatch → Dashboards
2. Откройте `callsum-monitoring-prod`

**Метрики:**
- Lambda invocations
- Lambda errors
- Lambda duration
- DynamoDB capacity
- API Gateway requests

---

### 6.2 Cost Explorer

1. AWS Console → Cost Management → Cost Explorer
2. Фильтр по тегу: `Project: Callsum`

**Ожидаемые расходы (первый месяц):**
- S3: $0.50
- Lambda: $0.20
- DynamoDB: $0.25
- API Gateway: $0.35
- Secrets Manager: $1.20
- **AWS Total: ~$2.50**
- RunPod: ~$10-15 (зависит от использования)
- **ИТОГО: ~$12-18/месяц**

---

### 6.3 Budget Alerts

Вы получите email уведомления при:
- 50% бюджета
- 80% бюджета
- 100% бюджета

---

## 🛠 ЧАСТЬ 7: Troubleshooting

### Проблема: "Rate limit exceeded"

**Причина:** Превышен лимит 10 запросов/час или 50/день

**Решение:**
1. Подождите час
2. Или увеличьте лимиты в `terraform.tfvars`:
   ```hcl
   FREE_TIER_REQUESTS_PER_HOUR = 20
   FREE_TIER_REQUESTS_PER_DAY = 100
   ```
3. `terraform apply`

---

### Проблема: "GPU timeout"

**Причина:** Очень длинное аудио (>2 часа)

**Решение:**
1. Разделите аудио на части
2. Или увеличьте timeout в `terraform.tfvars`:
   ```hcl
   RUNPOD_TIMEOUT_SECONDS = 7200  # 2 часа
   ```

---

### Проблема: "Out of memory" в RunPod

**Причина:** VRAM недостаточно на RTX 3090

**Решение:**
1. RunPod Console → Endpoint Settings
2. Измените GPU Type на **RTX 4090** или **A40**
3. Сохраните

---

### Проблема: Webhook не работает

**Проверка:**
```bash
curl "https://api.telegram.org/bot<токен>/getWebhookInfo"
```

**Если `last_error_date` не 0:**
1. Проверьте Lambda логи
2. Проверьте что secret_token совпадает
3. Переустановите webhook

---

## 🔄 ЧАСТЬ 8: Обновление проекта

### 8.1 Обновление Lambda кода

```bash
./deployment/build_lambda_package.sh

cd infrastructure/terraform
terraform apply
```

---

### 8.2 Обновление RunPod образа

```bash
cd runpod_service
docker build --build-arg HF_TOKEN=$HF_TOKEN -t callsum-ml:latest .
docker tag callsum-ml:latest <username>/callsum-ml:latest
docker push <username>/callsum-ml:latest
```

**RunPod автоматически подтянет новый образ при следующем запуске.**

---

### 8.3 Обновление инфраструктуры

```bash
cd infrastructure/terraform
terraform plan   # Проверка изменений
terraform apply  # Применение
```

---

## 🗑 ЧАСТЬ 9: Удаление проекта

**Если нужно удалить все ресурсы:**

```bash
cd infrastructure/terraform
terraform destroy
```

**Подтвердите ввод `yes`**

**⚠️ ВНИМАНИЕ:** Это удалит:
- Все данные в S3
- Все записи в DynamoDB
- Lambda функции
- API Gateway
- Secrets

**RunPod:**
1. RunPod Console → Endpoints
2. Удалите endpoint вручную

---

## 📞 Поддержка

**Логи:**
- CloudWatch: `/aws/lambda/callsum-lambda-telegram-bot-prod`
- RunPod: Console → Endpoints → Logs

**Проблемы:**
- Проверьте секцию Troubleshooting выше
- Проверьте CloudWatch Dashboard

---

## 🎉 Готово!

Ваш Callsum бот запущен и готов к использованию!

**Следующие шаги:**
1. Протестируйте с разными типами аудио
2. Настройте мониторинг расходов
3. Поделитесь ботом с командой
4. Соберите feedback для улучшений

**Полезные ссылки:**
- AWS Console: https://console.aws.amazon.com
- RunPod Console: https://www.runpod.io/console
- CloudWatch Logs: https://console.aws.amazon.com/cloudwatch
- Cost Explorer: https://console.aws.amazon.com/cost-management
