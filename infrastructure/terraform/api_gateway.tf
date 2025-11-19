# API Gateway для Telegram Webhook

resource "aws_api_gateway_rest_api" "telegram_webhook" {
  name        = "${local.project_name}-telegram-webhook-${var.environment}"
  description = "API Gateway для Telegram Bot Webhook"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = merge(local.common_tags, {
    Name = "Telegram Webhook API"
  })
}

# Webhook Resource
resource "aws_api_gateway_resource" "webhook" {
  rest_api_id = aws_api_gateway_rest_api.telegram_webhook.id
  parent_id   = aws_api_gateway_rest_api.telegram_webhook.root_resource_id
  path_part   = "webhook"
}

# Health Check Resource
resource "aws_api_gateway_resource" "health" {
  rest_api_id = aws_api_gateway_rest_api.telegram_webhook.id
  parent_id   = aws_api_gateway_rest_api.telegram_webhook.root_resource_id
  path_part   = "health"
}

# POST method for webhook
resource "aws_api_gateway_method" "webhook_post" {
  rest_api_id   = aws_api_gateway_rest_api.telegram_webhook.id
  resource_id   = aws_api_gateway_resource.webhook.id
  http_method   = "POST"
  authorization = "NONE"  # Telegram не поддерживает auth headers
}

# GET method for health check
resource "aws_api_gateway_method" "health_get" {
  rest_api_id   = aws_api_gateway_rest_api.telegram_webhook.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "NONE"
}

# Health check mock integration (без Lambda)
resource "aws_api_gateway_integration" "health_mock" {
  rest_api_id = aws_api_gateway_rest_api.telegram_webhook.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# Health check response
resource "aws_api_gateway_method_response" "health_200" {
  rest_api_id = aws_api_gateway_rest_api.telegram_webhook.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  status_code = "200"

  response_models = {
    "application/json" = "Empty"
  }

  response_parameters = {
    "method.response.header.Content-Type" = true
  }
}

resource "aws_api_gateway_integration_response" "health_200" {
  rest_api_id = aws_api_gateway_rest_api.telegram_webhook.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_get.http_method
  status_code = aws_api_gateway_method_response.health_200.status_code

  response_templates = {
    "application/json" = jsonencode({
      status = "healthy"
      service = "callsum-api"
      timestamp = "$context.requestTime"
      version = "1.0.0"
    })
  }
}

# Lambda integration
resource "aws_api_gateway_integration" "webhook_lambda" {
  rest_api_id = aws_api_gateway_rest_api.telegram_webhook.id
  resource_id = aws_api_gateway_resource.webhook.id
  http_method = aws_api_gateway_method.webhook_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.telegram_bot.invoke_arn
}

# Deployment
resource "aws_api_gateway_deployment" "webhook" {
  depends_on = [
    aws_api_gateway_integration.webhook_lambda,
    aws_api_gateway_integration.health_mock
  ]

  rest_api_id = aws_api_gateway_rest_api.telegram_webhook.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.webhook.id,
      aws_api_gateway_method.webhook_post.id,
      aws_api_gateway_integration.webhook_lambda.id,
      aws_api_gateway_resource.health.id,
      aws_api_gateway_method.health_get.id,
      aws_api_gateway_integration.health_mock.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Stage
resource "aws_api_gateway_stage" "webhook" {
  deployment_id = aws_api_gateway_deployment.webhook.id
  rest_api_id   = aws_api_gateway_rest_api.telegram_webhook.id
  stage_name    = var.environment

  # Логирование
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      caller         = "$context.identity.caller"
      user           = "$context.identity.user"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  # X-Ray tracing
  xray_tracing_enabled = true

  tags = merge(local.common_tags, {
    Name = "Webhook Stage"
  })
}

# Method Settings (throttling, logging)
resource "aws_api_gateway_method_settings" "webhook" {
  rest_api_id = aws_api_gateway_rest_api.telegram_webhook.id
  stage_name  = aws_api_gateway_stage.webhook.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled    = true
    logging_level      = "INFO"
    data_trace_enabled = false  # Не логируем тело запросов (конфиденциальность)

    # Throttling (защита от DDoS)
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }
}

# CloudWatch Log Group для API Gateway
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${aws_api_gateway_rest_api.telegram_webhook.name}"
  retention_in_days = 7

  tags = merge(local.common_tags, {
    Name = "API Gateway Logs"
  })
}

# Outputs
output "api_gateway_url" {
  description = "URL для Telegram Webhook"
  value       = "${aws_api_gateway_stage.webhook.invoke_url}/webhook"
}

output "health_check_url" {
  description = "URL для Health Check (для мониторинга)"
  value       = "${aws_api_gateway_stage.webhook.invoke_url}/health"
}

output "api_gateway_id" {
  description = "ID API Gateway"
  value       = aws_api_gateway_rest_api.telegram_webhook.id
}
