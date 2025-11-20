# 🌊 Использование DigitalOcean Spaces вместо AWS S3

## Зачем использовать DigitalOcean Spaces?

**Преимущества:**
- 💰 **Дешевле** - $5/месяц за 250GB (vs AWS S3 ~$6-10/месяц)
- 🌍 **Проще ценообразование** - фиксированная цена, нет сюрпризов
- 🔌 **S3-совместимость** - работает с boto3 "из коробки"

**Недостатки:**
- ❌ Нет автоматического управления через Terraform (нужно создавать Space вручную)
- ❌ Меньше регионов чем у AWS
- ❌ Нет версионирования и lifecycle policies через API

---

## 📋 Пошаговая инструкция

### Шаг 1: Создание DigitalOcean аккаунта

1. Перейдите на https://www.digitalocean.com
2. Зарегистрируйтесь
3. Привяжите банковскую карту
4. **Бонус:** Используйте промо-код для $200 credit (если доступен)

---

### Шаг 2: Создание Space

1. В панели управления: **Manage → Spaces Object Storage**
2. Нажмите **Create a Space**
3. **Выберите регион:**
   - `fra1` - Frankfurt, Germany (Европа)
   - `nyc3` - New York, USA (Северная Америка)
   - `sgp1` - Singapore (Азия)
   - `sfo3` - San Francisco, USA
   - `ams3` - Amsterdam, Netherlands
4. **Имя Space:** `callsum-prod-<ваши-инициалы>`
   - ⚠️ Должно совпадать с `s3_bucket_name` в terraform.tfvars
   - Должно быть уникально глобально
5. **Enable CDN:** No (не нужно для приватных данных)
6. **Choose a project:** Default (или создайте новый)
7. Нажмите **Create a Space**

**💰 Стоимость:** $5/месяц (включает 250GB хранилища + 1TB трафика)

---

### Шаг 3: Получение API ключей

1. В панели: **API → Spaces Keys**
2. Нажмите **Generate New Key**
3. **Name:** `callsum-production`
4. Нажмите **Generate Key**
5. **Сохраните:**
   - **Access Key** (например: `DO00ABC...XYZ`)
   - **Secret Key** (показывается только один раз!)

⚠️ **ВАЖНО:** Secret Key нельзя восстановить! Сохраните в безопасное место.

---

### Шаг 4: Настройка Terraform

Отредактируйте `infrastructure/terraform/terraform.tfvars`:

```hcl
# === DIGITALOCEAN SPACES ===
use_digitalocean_spaces = true

# Endpoint (замените fra1 на ваш регион)
s3_endpoint = "https://fra1.digitaloceanspaces.com"

# Ключи из Шага 3
s3_access_key = "DO00ABC...XYZ"
s3_secret_key = "ваш_secret_key_здесь"

# Имя Space (должно совпадать с созданным в Шаге 2)
s3_bucket_name = "callsum-prod-ваши-инициалы"
```

---

### Шаг 5: Настройка RunPod Environment Variables

В RunPod Endpoint Settings добавьте:

```bash
S3_ENDPOINT_URL=https://fra1.digitaloceanspaces.com
AWS_ACCESS_KEY_ID=DO00ABC...XYZ
AWS_SECRET_ACCESS_KEY=ваш_secret_key
AWS_REGION=us-east-1  # Можно оставить любой
```

---

### Шаг 6: Деплой

```bash
cd infrastructure/terraform
terraform init
terraform plan  # Проверьте что AWS S3 bucket НЕ создается
terraform apply
```

**Ожидаемый вывод:**
```
Plan: 14 to add, 0 to change, 0 to destroy.
# НЕ должно быть: aws_s3_bucket.callsum_storage
```

---

## ✅ Проверка работоспособности

### 1. Проверка через CLI

```bash
# Установите s3cmd
brew install s3cmd  # macOS
# или
sudo apt install s3cmd  # Linux

# Конфигурация
s3cmd --configure
# Введите DO Access Key и Secret
# Host: fra1.digitaloceanspaces.com
# S3 Endpoint: fra1.digitaloceanspaces.com

# Проверка
s3cmd ls s3://callsum-prod-ваши-инициалы/
```

---

### 2. Проверка через Python

```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='https://fra1.digitaloceanspaces.com',
    aws_access_key_id='DO00ABC...XYZ',
    aws_secret_access_key='ваш_secret_key',
    region_name='us-east-1'
)

# Список файлов
response = s3.list_objects_v2(Bucket='callsum-prod-ваши-инициалы')
print(response)
```

---

### 3. Тест бота

1. Отправьте голосовое сообщение боту
2. Проверьте DigitalOcean Spaces → ваш Space → Files
3. Должна появиться папка `users/<user_id>/audio/new/`

---

## 🔄 Миграция с AWS S3 на DigitalOcean Spaces

Если у вас уже есть данные в AWS S3:

### Вариант 1: AWS CLI (бесплатно)

```bash
# Установка
pip install awscli

# Настройка AWS credentials
aws configure

# Синхронизация
aws s3 sync s3://старый-aws-bucket s3://новый-do-space \
  --endpoint-url https://fra1.digitaloceanspaces.com
```

### Вариант 2: rclone (рекомендуется для больших объемов)

```bash
# Установка
brew install rclone  # macOS
# или скачайте с https://rclone.org

# Конфигурация AWS S3
rclone config
# Выберите S3 → AWS credentials

# Конфигурация DO Spaces
rclone config
# Выберите S3 → Custom endpoint → fra1.digitaloceanspaces.com

# Копирование
rclone copy aws-s3:старый-bucket do-spaces:новый-bucket
```

---

## 💰 Сравнение стоимости

### AWS S3

| Параметр | Стоимость |
|----------|-----------|
| Хранилище (250GB) | $5.75/месяц |
| Запросы PUT (10k) | $0.05 |
| Запросы GET (100k) | $0.04 |
| Трафик (100GB) | $9.00 |
| **ИТОГО** | ~$15/месяц |

### DigitalOcean Spaces

| Параметр | Стоимость |
|----------|-----------|
| Хранилище (250GB) | $5/месяц |
| Все запросы | Включено |
| Трафик (1TB) | Включено |
| **ИТОГО** | **$5/месяц** |

**Экономия: ~$10/месяц (~66%)**

---

## 🛠 Troubleshooting

### Проблема: "Access Denied"

**Причина:** Неверные credentials

**Решение:**
1. Проверьте что Access Key и Secret Key корректны
2. Убедитесь что endpoint правильный (`https://регион.digitaloceanspaces.com`)
3. Проверьте что Space существует и имя совпадает

---

### Проблема: "NoSuchBucket"

**Причина:** Space не создан или неверное имя

**Решение:**
1. Создайте Space через DigitalOcean панель
2. Убедитесь что `s3_bucket_name` в terraform.tfvars совпадает с именем Space

---

### Проблема: Presigned URLs не работают

**Причина:** DigitalOcean требует virtual-hosted-style URLs

**Решение:** Код уже учитывает это (boto3 автоматически обрабатывает)

---

## 🔙 Возврат на AWS S3

Если нужно вернуться на AWS S3:

```hcl
# terraform.tfvars
use_digitalocean_spaces = false

# Закомментируйте DO credentials
# s3_endpoint = "..."
# s3_access_key = "..."
# s3_secret_key = "..."
```

```bash
terraform apply
```

Terraform создаст AWS S3 bucket и обновит Lambda environment variables.

---

## 📚 Дополнительные ресурсы

- [DigitalOcean Spaces Documentation](https://docs.digitalocean.com/products/spaces/)
- [S3 API Compatibility](https://docs.digitalocean.com/products/spaces/reference/s3-compatibility/)
- [Spaces Pricing](https://www.digitalocean.com/pricing/spaces)

---

## ✅ Checklist готовности

- [ ] DigitalOcean аккаунт создан
- [ ] Space создан с правильным именем
- [ ] API Keys получены и сохранены
- [ ] `terraform.tfvars` обновлен
- [ ] RunPod environment variables настроены
- [ ] `terraform apply` выполнен успешно
- [ ] Тест бота прошел успешно
- [ ] Файлы появляются в DigitalOcean Space

---

**Готово!** Теперь ваш Callsum использует DigitalOcean Spaces для хранения файлов 🎉
