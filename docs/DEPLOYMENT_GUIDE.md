# 📚 CALLSUM - ПОЛНОЕ РУКОВОДСТВО ПО ДЕПЛОЮ

Это руководство проведет вас через весь процесс развертывания Callsum - от нуля до полностью работающей системы.

## 📋 СОДЕРЖАНИЕ

1. [Предварительные требования](#prerequisites)
2. [Регистрация сервисов](#registration)
3. [Локальная настройка](#local-setup)
4. [Деплой AWS инфраструктуры](#aws-deployment)
5. [Деплой ML сервиса на RunPod](#runpod-deployment)
6. [Настройка Telegram бота](#telegram-setup)
7. [Тестирование](#testing)
8. [Мониторинг](#monitoring)
9. [Troubleshooting](#troubleshooting)

---

## <a name="prerequisites"></a>1️⃣ ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ

### Установите инструменты:

1. **Git**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install git

   # macOS
   brew install git
   ```

2. **Docker**
   - Скачайте: https://docs.docker.com/get-docker/
   - Проверка: `docker --version`

3. **Terraform**
   ```bash
   # Ubuntu/Debian
   wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
   unzip terraform_1.6.6_linux_amd64.zip
   sudo mv terraform /usr/local/bin/

   # macOS
   brew install terraform
   ```
   - Проверка: `terraform --version`

4. **AWS CLI**
   ```bash
   # Ubuntu/Debian
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install

   # macOS
   brew install awscli
   ```
   - Проверка: `aws --version`

---

## <a name="registration"></a>2️⃣ РЕГИСТРАЦИЯ СЕРВИСОВ

### 2.1 AWS

1. Создайте аккаунт: https://aws.amazon.com/
2. Настройте IAM пользователя с правами:
   - AmazonS3FullAccess
   - AmazonDynamoDBFullAccess
   - AWSLambdaFullAccess
   - AmazonAPIGatewayAdministrator
   - SecretsManagerReadWrite
3. Получите Access Key ID и Secret Access Key
4. Настройте AWS CLI:
   ```bash
   aws configure
   # AWS Access Key ID: <ваш ключ>
   # AWS Secret Access Key: <ваш секрет>
   # Default region: us-east-1
   # Default output format: json
   ```

### 2.2 RunPod

1. Регистрация: https://www.runpod.io/console/signup
2. Пополните баланс ($10 минимум)
3. Получите API Key:
   - Settings → API Keys → Create API Key
   - Сохраните ключ!

### 2.3 Hugging Face

1. Регистрация: https://huggingface.co/join
2. Получите токен:
   - Settings → Access Tokens → New token
   - Type: Read
   - Сохраните токен!

### 2.4 Telegram Bot

1. Откройте Telegram, найдите @BotFather
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Сохраните Bot Token (выглядит как `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

---

## <a name="local-setup"></a>3️⃣ ЛОКАЛЬНАЯ НАСТРОЙКА

### 3.1 Клонируйте репозиторий

```bash
git clone <repository-url>
cd Callsum
```

### 3.2 Настройте Terraform переменные

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars
```

Заполните:
```hcl
# AWS
aws_region  = "us-east-1"
environment = "prod"

# Telegram
telegram_bot_token = "123456:ABC-DEF..."  # Ваш токен

# Hugging Face
hf_token = "hf_..."  # Ваш токен

# RunPod (заполните после создания endpoint)
runpod_api_key      = "временно-оставьте-пустым"
runpod_endpoint_url = "временно-оставьте-пустым"

# S3 (имя должно быть уникальным глобально!)
s3_bucket_name      = "callsum-prod-ВАШ-УНИКАЛЬНЫЙ-ID"
dynamodb_table_name = "callsum-jobs"
```

---

## <a name="aws-deployment"></a>4️⃣ ДЕПЛОЙ AWS ИНФРАСТРУКТУРЫ

### 4.1 Автоматический деплой

```bash
cd deployment
./deploy_aws.sh
```

Скрипт выполнит:
- ✅ Проверку зависимостей
- ✅ Terraform init, validate, plan
- ✅ Создание инфраструктуры (после вашего подтверждения)
- ✅ Вывод итоговой информации

### 4.2 Ручной деплой (альтернатива)

```bash
cd infrastructure/terraform

# Инициализация
terraform init

# Проверка конфигурации
terraform validate

# Просмотр плана
terraform plan

# Применение (создание инфраструктуры)
terraform apply

# Сохранение outputs
terraform output -json > outputs.json
```

### 4.3 Что будет создано?

- **S3 Bucket** - хранение аудио и результатов (шифрование AES-256)
- **SQS Queue** - очередь задач + Dead Letter Queue
- **DynamoDB Table** - метаданные задач
- **Lambda Function** - Telegram бот
- **API Gateway** - webhook для Telegram
- **Secrets Manager** - хранение токенов
- **IAM Roles** - права доступа
- **CloudWatch** - логи и метрики

### 4.4 Стоимость

Примерно **$1-3/месяц** при нагрузке 60 часов аудио/месяц:
- S3: ~$1
- Lambda: ~$0.50
- DynamoDB: ~$0.30
- API Gateway: ~$0.10
- SQS: бесплатно (в пределах Free Tier)

---

## <a name="runpod-deployment"></a>5️⃣ ДЕПЛОЙ ML СЕРВИСА НА RUNPOD

### 5.1 Подготовка Docker образа

```bash
cd runpod_service

# Экспортируйте HF_TOKEN
export HF_TOKEN=your_hf_token_here

# Соберите Docker образ
docker build -t callsum/ml-service:latest .
```

### 5.2 Push в Docker Registry

**Вариант A: Docker Hub**

```bash
# Логин
docker login -u ВАШ_USERNAME

# Tag
docker tag callsum/ml-service:latest ВАШ_USERNAME/callsum-ml-service:latest

# Push
docker push ВАШ_USERNAME/callsum-ml-service:latest
```

**Вариант B: AWS ECR**

```bash
# Создайте ECR repository
aws ecr create-repository --repository-name callsum-ml-service

# Получите login команду
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag и Push
docker tag callsum/ml-service:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/callsum-ml-service:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/callsum-ml-service:latest
```

### 5.3 Создание RunPod Serverless Endpoint

1. Откройте https://www.runpod.io/console/serverless
2. Нажмите **"+ New Endpoint"**
3. Заполните:
   - **Name**: `callsum-ml-service`
   - **Docker Image**: `ВАШ_USERNAME/callsum-ml-service:latest`
   - **GPU Type**: NVIDIA RTX 3090 ($0.44/час)
   - **Container Disk**: 20 GB
   - **Min Workers**: 0 (serverless - платите только за использование)
   - **Max Workers**: 1 (для начала)
   - **Idle Timeout**: 5 минут

4. **Environment Variables**:
   ```
   HF_TOKEN=ваш_hf_token
   ```

5. Нажмите **"Deploy"**

6. Скопируйте:
   - **Endpoint ID**
   - **API Key**

### 5.4 Обновите Terraform

```bash
cd infrastructure/terraform

# Отредактируйте terraform.tfvars
nano terraform.tfvars
```

Добавьте:
```hcl
runpod_api_key      = "ВАШ_RUNPOD_API_KEY"
runpod_endpoint_url = "https://api.runpod.ai/v2/ENDPOINT_ID/run"
```

Примените изменения:
```bash
terraform apply
```

---

## <a name="telegram-setup"></a>6️⃣ НАСТРОЙКА TELEGRAM БОТА

### 6.1 Получите Webhook URL

```bash
cd infrastructure/terraform
WEBHOOK_URL=$(terraform output -raw api_gateway_url)
echo $WEBHOOK_URL
```

### 6.2 Установите Webhook

```bash
curl -X POST "https://api.telegram.org/bot<ВАШ_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$WEBHOOK_URL\"}"
```

Ожидаемый ответ:
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

### 6.3 Проверьте Webhook

```bash
curl "https://api.telegram.org/bot<ВАШ_BOT_TOKEN>/getWebhookInfo"
```

Должно быть:
```json
{
  "ok": true,
  "result": {
    "url": "ВАШ_WEBHOOK_URL",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

---

## <a name="testing"></a>7️⃣ ТЕСТИРОВАНИЕ

### 7.1 Базовый тест

1. Откройте Telegram
2. Найдите вашего бота (по username)
3. Отправьте `/start`

Ожидаемый ответ:
```
👋 Привет! Я бот для анализа звонков.
...
```

### 7.2 Тест обработки аудио

1. Запишите голосовое сообщение (10-30 секунд)
2. Отправьте боту
3. Дождитесь ответа (~1-2 минуты для короткого аудио)

### 7.3 Проверка логов

**AWS CloudWatch:**
```bash
aws logs tail /aws/lambda/callsum-telegram-bot-prod --follow
```

**RunPod Dashboard:**
- Откройте https://www.runpod.io/console/serverless
- Выберите ваш endpoint
- Перейдите в "Logs"

---

## <a name="monitoring"></a>8️⃣ МОНИТОРИНГ

### 8.1 CloudWatch Dashboards

Создайте дашборд:
```bash
aws cloudwatch put-dashboard --dashboard-name Callsum --dashboard-body file://cloudwatch-dashboard.json
```

Метрики для отслеживания:
- Lambda errors
- Lambda duration
- SQS queue depth
- DynamoDB throttles
- API Gateway 4xx/5xx

### 8.2 Cost Explorer

Отслеживайте затраты:
- https://console.aws.amazon.com/cost-management/home

### 8.3 RunPod Analytics

- https://www.runpod.io/console/serverless
- Вкладка "Analytics"
- Метрики:
  - Execution time
  - Cold starts
  - Costs

---

## <a name="troubleshooting"></a>9️⃣ TROUBLESHOOTING

### Проблема: Бот не отвечает

**Решение:**
1. Проверьте webhook:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   ```

2. Проверьте логи Lambda:
   ```bash
   aws logs tail /aws/lambda/callsum-telegram-bot-prod --follow
   ```

3. Проверьте API Gateway:
   - AWS Console → API Gateway → callsum-telegram-webhook-prod
   - Вкладка "Logs"

### Проблема: RunPod не запускается

**Решение:**
1. Проверьте Docker образ локально:
   ```bash
   docker run --gpus all -e HF_TOKEN=$HF_TOKEN callsum/ml-service:latest
   ```

2. Проверьте логи RunPod:
   - RunPod Console → Endpoint → Logs

3. Проверьте environment variables в RunPod

### Проблема: Ошибка "S3 Access Denied"

**Решение:**
1. Проверьте IAM роль Lambda:
   ```bash
   aws iam get-role-policy --role-name callsum-lambda-telegram-bot-prod --policy-name callsum-lambda-telegram-bot-policy
   ```

2. Проверьте S3 bucket policy:
   ```bash
   aws s3api get-bucket-policy --bucket callsum-prod
   ```

### Проблема: Высокие затраты

**Решение:**
1. Проверьте RunPod Idle Timeout (должен быть 5 мин)
2. Проверьте S3 Lifecycle rules (автоудаление старых файлов)
3. Уменьшите Lambda memory (если не используется)

---

## 🎉 ГОТОВО!

Ваш Callsum развернут и готов к работе!

**Полезные ссылки:**
- AWS Console: https://console.aws.amazon.com/
- RunPod Console: https://www.runpod.io/console
- Telegram Bot API: https://core.telegram.org/bots/api

**Поддержка:**
- GitHub Issues: <repository-url>/issues
- Email: support@your-domain.com

---

## 📊 АРХИТЕКТУРА

```
[Telegram User]
      ↓
[Telegram Bot API]
      ↓
[API Gateway] → [Lambda] → [S3] → [SQS]
                    ↓           ↓
              [DynamoDB]   [RunPod GPU]
                              ↓
                        [Whisper + Pyannote + Llama]
                              ↓
                            [S3]
                              ↓
                        [Telegram User]
```

**Стоимость:** ~$10-15/месяц при 60 часах аудио
**Время обработки:** ~20 минут на 1 час аудио
**Безопасность:** ✅ Шифрование, ✅ Изоляция, ✅ Минимальные права
