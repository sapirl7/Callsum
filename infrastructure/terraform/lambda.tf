# Lambda функция для Telegram бота

# Архив с кодом Lambda (предполагается что код уже собран)
data "archive_file" "telegram_bot_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../../telegram_bot"
  output_path = "${path.module}/telegram_bot_lambda.zip"
  excludes = [
    "bot_local.py",
    "__pycache__",
    "*.pyc",
    ".env"
  ]
}

# Lambda функция
resource "aws_lambda_function" "telegram_bot" {
  filename      = data.archive_file.telegram_bot_lambda.output_path
  function_name = "${local.project_name}-telegram-bot-${var.environment}"
  role          = aws_iam_role.lambda_telegram_bot.arn
  handler       = "bot.lambda_handler"
  runtime       = "python3.10"

  source_code_hash = data.archive_file.telegram_bot_lambda.output_base64sha256

  timeout     = var.lambda_timeout
  memory_size = var.lambda_memory

  environment {
    variables = {
      # AWS Resources
      S3_BUCKET_NAME      = aws_s3_bucket.callsum_storage.id
      SQS_QUEUE_URL       = aws_sqs_queue.callsum_jobs.url
      DYNAMODB_TABLE_NAME = aws_dynamodb_table.callsum_jobs.name
      AWS_REGION          = var.aws_region
      ENVIRONMENT         = var.environment

      # Secrets Manager ARNs (Lambda fetches actual values)
      TELEGRAM_BOT_TOKEN_SECRET_ARN = aws_secretsmanager_secret.telegram_bot_token.arn
      RUNPOD_API_KEY_SECRET_ARN     = aws_secretsmanager_secret.runpod_api_key.arn

      # RunPod Configuration
      RUNPOD_ENDPOINT_URL = var.runpod_endpoint_url
      CALLBACK_URL        = "${aws_api_gateway_stage.webhook.invoke_url}/webhook"

      # Application Configuration (from config.py)
      MAX_AUDIO_DURATION_SECONDS    = "7200"
      MIN_AUDIO_DURATION_SECONDS    = "1"
      MAX_FILE_SIZE_MB              = "100"
      FREE_TIER_REQUESTS_PER_HOUR   = "10"
      FREE_TIER_REQUESTS_PER_DAY    = "50"
      RUNPOD_TIMEOUT_SECONDS        = "3600"
      MAX_RETRIES                   = "3"
      RETRY_BACKOFF_MULTIPLIER      = "2"
      RETRY_MIN_WAIT_SECONDS        = "2"
      RETRY_MAX_WAIT_SECONDS        = "10"
      TELEGRAM_MAX_MESSAGE_LENGTH   = "4000"
    }
  }

  # Для продакшена можно добавить VPC config
  # vpc_config {
  #   subnet_ids         = var.subnet_ids
  #   security_group_ids = var.security_group_ids
  # }

  tags = merge(local.common_tags, {
    Name = "Telegram Bot Handler"
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "telegram_bot" {
  name              = "/aws/lambda/${aws_lambda_function.telegram_bot.function_name}"
  retention_in_days = 7  # Храним логи 7 дней

  tags = merge(local.common_tags, {
    Name = "Telegram Bot Logs"
  })
}

# Lambda Permission для API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.telegram_bot.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.telegram_webhook.execution_arn}/*/*"
}

# CloudWatch Alarms для мониторинга
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${local.project_name}-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert on Lambda errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.telegram_bot.function_name
  }

  # Отправляем алерты в SNS
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${local.project_name}-lambda-duration-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 50000  # 50 секунд
  alarm_description   = "Alert on high Lambda duration"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.telegram_bot.function_name
  }

  # Отправляем алерты в SNS
  alarm_actions = [aws_sns_topic.alerts.arn]
}

# Outputs
output "lambda_function_arn" {
  description = "ARN Lambda функции"
  value       = aws_lambda_function.telegram_bot.arn
}

output "lambda_function_name" {
  description = "Имя Lambda функции"
  value       = aws_lambda_function.telegram_bot.function_name
}
