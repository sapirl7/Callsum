<![CDATA[# Terraform Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "telegram_bot_token" {
  description = "Telegram Bot Token (stored in Secrets Manager)"
  type        = string
  sensitive   = true
}

variable "telegram_secret_token" {
  description = "Secret token to protect Telegram webhook from forged requests"
  type        = string
  sensitive   = true
}

variable "runpod_callback_token" {
  description = "Separate token for authenticating callback requests from RunPod. If empty, telegram_secret_token is used."
  type        = string
  sensitive   = true
  default     = ""
}

variable "hf_token" {
  description = "Hugging Face Token for Pyannote"
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
  description = "S3 bucket name for audio storage"
  type        = string
  default     = "callsum-prod"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for jobs"
  type        = string
  default     = "callsum-jobs"
}

variable "lambda_timeout" {
  description = "Lambda function timeout (seconds)"
  type        = number
  default     = 60
}

variable "lambda_memory" {
  description = "Lambda function memory (MB)"
  type        = number
  default     = 512
}

variable "alert_email" {
  description = "Email for receiving alerts (optional)"
  type        = string
  default     = ""
}

variable "monthly_budget_limit" {
  description = "Monthly spending limit in USD"
  type        = number
  default     = 25
}

variable "runpod_monthly_limit" {
  description = "Monthly RunPod limit in USD"
  type        = number
  default     = 15
}

variable "enable_cost_tracking" {
  description = "Enable detailed cost tracking"
  type        = bool
  default     = true
}

# === DigitalOcean Spaces Configuration (optional) ===
# Use if you want to store files in DO Spaces instead of AWS S3

variable "use_digitalocean_spaces" {
  description = "Use DigitalOcean Spaces instead of AWS S3"
  type        = bool
  default     = false
}

variable "s3_endpoint" {
  description = "S3-compatible endpoint (for DigitalOcean Spaces: https://<region>.digitaloceanspaces.com)"
  type        = string
  default     = ""
}

variable "s3_access_key" {
  description = "Access Key for S3-compatible storage (DigitalOcean Spaces Key)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "s3_secret_key" {
  description = "Secret Key for S3-compatible storage (DigitalOcean Spaces Secret)"
  type        = string
  sensitive   = true
  default     = ""
}

# === AI Models Configuration ===

variable "llm_language" {
  description = "Language for Whisper transcription (e.g., 'ru', 'en')"
  type        = string
  default     = "ru"
}

variable "custom_system_prompt" {
  description = "Custom system prompt for summarization (leave empty for default)"
  type        = string
  default     = ""
}
]]>
