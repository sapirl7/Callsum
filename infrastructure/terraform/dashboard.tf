# CloudWatch Dashboard для мониторинга всех компонентов

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${local.project_name}-dashboard-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # Lambda Metrics
      {
        type = "metric"
        x    = 0
        y    = 0
        width = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", { stat = "Sum", label = "Invocations" }],
            [".", "Errors", { stat = "Sum", label = "Errors" }],
            [".", "Throttles", { stat = "Sum", label = "Throttles" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Performance"
          period  = 300
        }
      },

      # Lambda Duration
      {
        type = "metric"
        x    = 12
        y    = 0
        width = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", { stat = "Average", label = "Avg Duration" }],
            ["...", { stat = "Maximum", label = "Max Duration" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Duration (ms)"
          period  = 300
          yAxis = {
            left = {
              label = "Milliseconds"
            }
          }
        }
      },

      # DynamoDB Metrics
      {
        type = "metric"
        x    = 0
        y    = 6
        width = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", { stat = "Sum" }],
            [".", "ConsumedWriteCapacityUnits", { stat = "Sum" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "DynamoDB Capacity"
          period  = 300
        }
      },

      # S3 Metrics
      {
        type = "metric"
        x    = 12
        y    = 6
        width = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/S3", "NumberOfObjects", { stat = "Average", label = "Object Count" }],
            [".", "BucketSizeBytes", { stat = "Average", label = "Bucket Size" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "S3 Storage"
          period  = 86400
        }
      },

      # API Gateway Metrics
      {
        type = "metric"
        x    = 0
        y    = 12
        width = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", { stat = "Sum", label = "Total Requests" }],
            [".", "4XXError", { stat = "Sum", label = "4xx Errors" }],
            [".", "5XXError", { stat = "Sum", label = "5xx Errors" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "API Gateway Requests"
          period  = 300
        }
      },

      # Text widget with key information
      {
        type = "text"
        x    = 0
        y    = 18
        width = 24
        height = 3

        properties = {
          markdown = <<-EOT
# Callsum Monitoring Dashboard

**Environment:** ${var.environment}
**Project:** ${local.project_name}
**Region:** ${var.aws_region}

---

**Health Check:** [GET /health](${aws_api_gateway_stage.webhook.invoke_url}/health)
**Webhook:** [POST /webhook](${aws_api_gateway_stage.webhook.invoke_url}/webhook)

**Key Metrics:**
- Lambda timeout: ${var.lambda_timeout}s
- Lambda memory: ${var.lambda_memory}MB
- Rate limits: ${var.enable_cost_tracking ? "Enabled" : "Disabled"}
- Budget alerts: Active

EOT
        }
      }
    ]
  })
}

output "dashboard_url" {
  description = "URL CloudWatch Dashboard"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}
