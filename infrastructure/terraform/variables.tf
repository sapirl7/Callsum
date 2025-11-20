# Terraform Variables

variable "aws_region" {
  description = "AWS регион для деплоя"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Окружение (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "telegram_bot_token" {
  description = "Telegram Bot Token (будет храниться в Secrets Manager)"
  type        = string
  sensitive   = true
}

variable "telegram_secret_token" {
  description = "Secret token для защиты Telegram webhook от поддельных запросов"
  type        = string
  sensitive   = true
}

variable "hf_token" {
  description = "Hugging Face Token для Pyannote"
  type        = string
  sensitive   = true
}

variable "runpod_api_key" {
  description = "RunPod API Key"
  type        = string
  sensitive   = true
}

variable "runpod_endpoint_url" {
  description = "RunPod Serverless Endpoint URL"
  type        = string
}

variable "s3_bucket_name" {
  description = "Имя S3 bucket для хранения аудио"
  type        = string
  default     = "callsum-prod"
}

variable "dynamodb_table_name" {
  description = "Имя DynamoDB таблицы для jobs"
  type        = string
  default     = "callsum-jobs"
}

variable "lambda_timeout" {
  description = "Timeout для Lambda функций (секунды)"
  type        = number
  default     = 60
}

variable "lambda_memory" {
  description = "Memory для Lambda функций (MB)"
  type        = number
  default     = 512
}

variable "alert_email" {
  description = "Email для получения алертов (опционально)"
  type        = string
  default     = ""
}

variable "monthly_budget_limit" {
  description = "Месячный лимит расходов в USD"
  type        = number
  default     = 25
}

variable "runpod_monthly_limit" {
  description = "Месячный лимит для RunPod в USD"
  type        = number
  default     = 15
}

variable "enable_cost_tracking" {
  description = "Включить детальное отслеживание расходов"
  type        = bool
  default     = true
}

# === DigitalOcean Spaces Configuration (опционально) ===
# Используйте если хотите хранить файлы в DO Spaces вместо AWS S3

variable "use_digitalocean_spaces" {
  description = "Использовать DigitalOcean Spaces вместо AWS S3"
  type        = bool
  default     = false
}

variable "s3_endpoint" {
  description = "S3-совместимый endpoint (для DigitalOcean Spaces: https://<region>.digitaloceanspaces.com)"
  type        = string
  default     = ""
}

variable "s3_access_key" {
  description = "Access Key для S3-совместимого хранилища (DigitalOcean Spaces Key)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "s3_secret_key" {
  description = "Secret Key для S3-совместимого хранилища (DigitalOcean Spaces Secret)"
  type        = string
  sensitive   = true
  default     = ""
}
