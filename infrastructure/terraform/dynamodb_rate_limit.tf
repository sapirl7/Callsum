# DynamoDB table for Rate Limiting

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
    type = "N" # Unix timestamp of window start
  }

  # TTL for automatic cleanup of old records (older than 24 hours)
  ttl {
    enabled        = true
    attribute_name = "ttl"
  }

  # Encryption
  server_side_encryption {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "Rate Limiting Tracker"
  })
}

# Outputs
output "rate_limits_table_name" {
  description = "Rate Limiting table name"
  value       = aws_dynamodb_table.rate_limits.name
}
