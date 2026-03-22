# IAM Roles and Policies for Lambda functions

# IAM Role for Telegram Bot Lambda
resource "aws_iam_role" "lambda_telegram_bot" {
  name = "${local.project_name}-lambda-telegram-bot-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "Telegram Bot Lambda Role"
  })
}

# Basic Lambda execution policy (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_telegram_bot.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Custom policy for AWS service access
resource "aws_iam_role_policy" "lambda_telegram_bot_policy" {
  name = "${local.project_name}-lambda-telegram-bot-policy"
  role = aws_iam_role.lambda_telegram_bot.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 access
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:PutObjectAcl"
        ]
        Resource = try("${aws_s3_bucket.callsum_storage[0].arn}/*", "arn:aws:s3:::*")
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = try(aws_s3_bucket.callsum_storage[0].arn, "arn:aws:s3:::*")
      },
      # DynamoDB access
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.callsum_jobs.arn,
          "${aws_dynamodb_table.callsum_jobs.arn}/index/*",
          aws_dynamodb_table.rate_limits.arn
        ]
      },
      # Secrets Manager access
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = compact([
          aws_secretsmanager_secret.telegram_bot_token.arn,
          aws_secretsmanager_secret.runpod_api_key.arn,
          try(aws_secretsmanager_secret.do_spaces_keys[0].arn, "")
        ])
      }
    ]
  })
}

# Outputs
output "lambda_role_arn" {
  description = "ARN of the Lambda IAM role"
  value       = aws_iam_role.lambda_telegram_bot.arn
}
