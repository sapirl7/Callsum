# Terraform Outputs - deployment summary

output "summary" {
  description = "Deployed infrastructure summary"
  value = {
    # API & Webhook
    webhook_url = "${aws_api_gateway_stage.webhook.invoke_url}/webhook"

    # Storage
    s3_bucket      = var.use_digitalocean_spaces ? var.s3_bucket_name : aws_s3_bucket.callsum_storage[0].id
    s3_bucket_arn  = var.use_digitalocean_spaces ? "N/A (using DigitalOcean Spaces)" : aws_s3_bucket.callsum_storage[0].arn

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
  description = "Next steps after deployment"
  value = <<-EOT

    INFRASTRUCTURE DEPLOYED!

    NEXT STEPS:

    1. Set Telegram Webhook:
       curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
         -H "Content-Type: application/json" \
         -d '{"url": "${aws_api_gateway_stage.webhook.invoke_url}/webhook"}'

    2. Verify webhook:
       curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

     3. Deploy Docker container to RunPod:
       cd deployment
       ./deploy_runpod.sh

    4. Test the bot:
       Send /start to the bot in Telegram

    5. Monitoring:
       - CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/
       - DynamoDB: ${aws_dynamodb_table.callsum_jobs.name}

    DASHBOARD:
     S3 Bucket: ${var.use_digitalocean_spaces ? var.s3_bucket_name : aws_s3_bucket.callsum_storage[0].id}
     Lambda: ${aws_lambda_function.telegram_bot.function_name}

  EOT
}
