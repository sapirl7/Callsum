# DynamoDB table for storing job metadata

resource "aws_dynamodb_table" "callsum_jobs" {
  name           = var.dynamodb_table_name
  billing_mode   = "PAY_PER_REQUEST"  # On-demand pricing (cost-effective for low traffic)
  hash_key       = "job_id"

  attribute {
    name = "job_id"
    type = "S"  # String
  }

  attribute {
    name = "user_id"
    type = "N"  # Number
  }

  attribute {
    name = "created_at"
    type = "S"  # ISO timestamp string
  }

  # Global Secondary Index for querying by user_id
  global_secondary_index {
    name            = "UserIdIndex"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # TTL for automatic cleanup of old records
  ttl {
    enabled        = true
    attribute_name = "ttl"  # Unix timestamp for deletion
  }

  # Point-in-time recovery for disaster recovery
  point_in_time_recovery {
    enabled = true
  }

  # Encryption at rest
  server_side_encryption {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name = "Callsum Jobs Metadata"
  })
}

# CloudWatch Alarm for monitoring errors
resource "aws_cloudwatch_metric_alarm" "dynamodb_errors" {
  alarm_name          = "${local.project_name}-dynamodb-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UserErrors"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Alert on DynamoDB user errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.callsum_jobs.name
  }
}

# Outputs
output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.callsum_jobs.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB table ARN"
  value       = aws_dynamodb_table.callsum_jobs.arn
}
