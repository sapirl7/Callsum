<![CDATA[# SNS Topic for CloudWatch alarms and notifications

resource "aws_sns_topic" "alerts" {
  name         = "${local.project_name}-alerts-${var.environment}"
  display_name = "Callsum Alerts"

  tags = merge(local.common_tags, {
    Name = "Alerts Topic"
  })
}

# Email subscription (must be confirmed manually after deployment)
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# IAM Policy for CloudWatch to publish to SNS
resource "aws_sns_topic_policy" "alerts" {
  arn = aws_sns_topic.alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "cloudwatch.amazonaws.com"
        }
        Action = [
          "SNS:Publish"
        ]
        Resource = aws_sns_topic.alerts.arn
      }
    ]
  })
}

# Outputs
output "sns_topic_arn" {
  description = "ARN of the alerts SNS topic"
  value       = aws_sns_topic.alerts.arn
}
]]>
