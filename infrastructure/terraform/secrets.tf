# AWS Secrets Manager для хранения токенов

# Telegram Bot Token
resource "aws_secretsmanager_secret" "telegram_bot_token" {
  name        = "${local.project_name}/telegram-bot-token-${var.environment}"
  description = "Telegram Bot Token"

  recovery_window_in_days = 7  # Можно восстановить в течение 7 дней после удаления

  tags = merge(local.common_tags, {
    Name = "Telegram Bot Token"
  })
}

resource "aws_secretsmanager_secret_version" "telegram_bot_token" {
  secret_id = aws_secretsmanager_secret.telegram_bot_token.id
  secret_string = jsonencode({
    token = var.telegram_bot_token
  })
}

# Hugging Face Token
resource "aws_secretsmanager_secret" "hf_token" {
  name        = "${local.project_name}/hf-token-${var.environment}"
  description = "Hugging Face Token для Pyannote"

  recovery_window_in_days = 7

  tags = merge(local.common_tags, {
    Name = "Hugging Face Token"
  })
}

resource "aws_secretsmanager_secret_version" "hf_token" {
  secret_id = aws_secretsmanager_secret.hf_token.id
  secret_string = jsonencode({
    token = var.hf_token
  })
}

# RunPod API Key
resource "aws_secretsmanager_secret" "runpod_api_key" {
  name        = "${local.project_name}/runpod-api-key-${var.environment}"
  description = "RunPod API Key"

  recovery_window_in_days = 7

  tags = merge(local.common_tags, {
    Name = "RunPod API Key"
  })
}

resource "aws_secretsmanager_secret_version" "runpod_api_key" {
  secret_id = aws_secretsmanager_secret.runpod_api_key.id
  secret_string = jsonencode({
    api_key = var.runpod_api_key
  })
}

# Outputs
output "telegram_bot_token_arn" {
  description = "ARN секрета с Telegram Bot Token"
  value       = aws_secretsmanager_secret.telegram_bot_token.arn
}

output "hf_token_arn" {
  description = "ARN секрета с HF Token"
  value       = aws_secretsmanager_secret.hf_token.arn
}

output "runpod_api_key_arn" {
  description = "ARN секрета с RunPod API Key"
  value       = aws_secretsmanager_secret.runpod_api_key.arn
}

# DigitalOcean Spaces Credentials (опционально)
resource "aws_secretsmanager_secret" "do_spaces_keys" {
  count       = var.use_digitalocean_spaces ? 1 : 0
  name        = "${local.project_name}/do-spaces-keys-${var.environment}"
  description = "DigitalOcean Spaces Credentials"

  recovery_window_in_days = 7

  tags = merge(local.common_tags, {
    Name = "DO Spaces Credentials"
  })
}

resource "aws_secretsmanager_secret_version" "do_spaces_keys" {
  count     = var.use_digitalocean_spaces ? 1 : 0
  secret_id = aws_secretsmanager_secret.do_spaces_keys[0].id
  secret_string = jsonencode({
    access_key = var.s3_access_key
    secret_key = var.s3_secret_key
  })
}

output "do_spaces_keys_arn" {
  description = "ARN секрета с DO Spaces ключами"
  value       = var.use_digitalocean_spaces ? aws_secretsmanager_secret.do_spaces_keys[0].arn : ""
}
