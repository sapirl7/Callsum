# SQS Queue для обработки задач

resource "aws_sqs_queue" "callsum_jobs" {
  name                       = "${local.project_name}-jobs-${var.environment}"
  delay_seconds              = 0
  max_message_size           = 262144  # 256 KB
  message_retention_seconds  = 86400   # 24 часа
  receive_wait_time_seconds  = 10      # Long polling
  visibility_timeout_seconds = 3600    # 1 час (время обработки GPU)

  # Dead Letter Queue для failed jobs
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.callsum_jobs_dlq.arn
    maxReceiveCount     = 3  # После 3 попыток → DLQ
  })

  tags = merge(local.common_tags, {
    Name = "Callsum Jobs Queue"
  })
}

# Dead Letter Queue
resource "aws_sqs_queue" "callsum_jobs_dlq" {
  name                      = "${local.project_name}-jobs-dlq-${var.environment}"
  message_retention_seconds = 1209600  # 14 дней

  tags = merge(local.common_tags, {
    Name = "Callsum Jobs DLQ"
  })
}

# SQS Policy для приема событий от S3
resource "aws_sqs_queue_policy" "callsum_jobs" {
  queue_url = aws_sqs_queue.callsum_jobs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.callsum_jobs.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_s3_bucket.callsum_storage.arn
          }
        }
      },
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda_telegram_bot.arn
        }
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.callsum_jobs.arn
      }
    ]
  })
}

# CloudWatch Alarm для мониторинга DLQ
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${local.project_name}-dlq-messages-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300  # 5 минут
  statistic           = "Average"
  threshold           = 0
  alarm_description   = "Alert when messages appear in DLQ"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.callsum_jobs_dlq.name
  }

  # Здесь можно добавить SNS topic для алертов
  # alarm_actions = [aws_sns_topic.alerts.arn]
}

# Outputs
output "sqs_queue_url" {
  description = "URL SQS очереди"
  value       = aws_sqs_queue.callsum_jobs.url
}

output "sqs_queue_arn" {
  description = "ARN SQS очереди"
  value       = aws_sqs_queue.callsum_jobs.arn
}

output "sqs_dlq_url" {
  description = "URL Dead Letter Queue"
  value       = aws_sqs_queue.callsum_jobs_dlq.url
}
