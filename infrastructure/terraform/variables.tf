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
