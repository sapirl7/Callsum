# DynamoDB таблица для Rate Limiting

resource "aws_dynamodb_table" "rate_limits" {
  name         = "${var.dynamodb_table_name}-rate-limits"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"
  range_key    = "window_start"

  attribute {
    name = "user_id"
    type = "N" # Number (Telegram user ID)
  }

  attribute {
    name = "window_start"
    type = "N" # Unix timestamp начала временного окна
  }

  # TTL для автоудаления старых записей (записи старше 24 часов)
  ttl {
    enabled        = true
    attribute_name = "ttl"
  }

  # Шифрование
  server_side_encryption {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "Rate Limiting Tracker"
  })
}

# Outputs
output "rate_limits_table_name" {
  description = "Имя таблицы Rate Limiting"
  value       = aws_dynamodb_table.rate_limits.name
}
