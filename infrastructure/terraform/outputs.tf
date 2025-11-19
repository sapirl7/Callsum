# Terraform Outputs - итоговая информация после деплоя

output "summary" {
  description = "Итоговая информация о развернутой инфраструктуре"
  value = {
    # API & Webhook
    webhook_url = "${aws_api_gateway_stage.webhook.invoke_url}/webhook"

    # Storage
    s3_bucket      = aws_s3_bucket.callsum_storage.id
    s3_bucket_arn  = aws_s3_bucket.callsum_storage.arn

    # Queue
    sqs_queue_url = aws_sqs_queue.callsum_jobs.url
    sqs_dlq_url   = aws_sqs_queue.callsum_jobs_dlq.url

    # Database
    dynamodb_table = aws_dynamodb_table.callsum_jobs.name

    # Lambda
    lambda_function = aws_lambda_function.telegram_bot.function_name
    lambda_arn      = aws_lambda_function.telegram_bot.arn

    # Secrets
    telegram_token_secret = aws_secretsmanager_secret.telegram_bot_token.name
    hf_token_secret       = aws_secretsmanager_secret.hf_token.name
    runpod_key_secret     = aws_secretsmanager_secret.runpod_api_key.name

    # Region
    aws_region  = var.aws_region
    environment = var.environment
  }
}

output "next_steps" {
  description = "Следующие шаги после деплоя"
  value = <<-EOT

    ✅ ИНФРАСТРУКТУРА РАЗВЕРНУТА!

    📝 СЛЕДУЮЩИЕ ШАГИ:

    1. Установите Telegram Webhook:
       curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
         -H "Content-Type: application/json" \
         -d '{"url": "${aws_api_gateway_stage.webhook.invoke_url}/webhook"}'

    2. Проверьте webhook:
       curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

    3. Деплой Docker контейнера на RunPod:
       cd runpod_service
       ./deploy.sh

    4. Протестируйте бота:
       Отправьте /start боту в Telegram

    5. Мониторинг:
       - CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/
       - SQS Queue: ${aws_sqs_queue.callsum_jobs.url}
       - DynamoDB: ${aws_dynamodb_table.callsum_jobs.name}

    📊 DASHBOARD:
    S3 Bucket: ${aws_s3_bucket.callsum_storage.id}
    Lambda: ${aws_lambda_function.telegram_bot.function_name}

  EOT
}
