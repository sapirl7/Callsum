# S3 Bucket для хранения аудио и результатов

resource "aws_s3_bucket" "callsum_storage" {
  bucket = var.s3_bucket_name

  tags = merge(local.common_tags, {
    Name = "Callsum Audio & Results Storage"
  })
}

# Включаем версионирование
resource "aws_s3_bucket_versioning" "callsum_storage" {
  bucket = aws_s3_bucket.callsum_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Включаем шифрование по умолчанию (AES-256)
resource "aws_s3_bucket_server_side_encryption_configuration" "callsum_storage" {
  bucket = aws_s3_bucket.callsum_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Блокируем публичный доступ
resource "aws_s3_bucket_public_access_block" "callsum_storage" {
  bucket = aws_s3_bucket.callsum_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle правила для автоудаления старых файлов
resource "aws_s3_bucket_lifecycle_configuration" "callsum_storage" {
  bucket = aws_s3_bucket.callsum_storage.id

  rule {
    id     = "delete-old-audio"
    status = "Enabled"

    filter {
      prefix = "users/"
    }

    expiration {
      days = 30  # Удаляем аудио старше 30 дней
    }

    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }

  rule {
    id     = "delete-old-results"
    status = "Enabled"

    filter {
      prefix = "users/"
    }

    expiration {
      days = 90  # Результаты храним 90 дней
    }
  }
}

# CORS конфигурация (если будет веб-интерфейс)
resource "aws_s3_bucket_cors_configuration" "callsum_storage" {
  bucket = aws_s3_bucket.callsum_storage.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = ["*"]  # В продакшене указать конкретные домены
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Outputs
output "s3_bucket_name" {
  description = "Имя S3 bucket"
  value       = aws_s3_bucket.callsum_storage.id
}

output "s3_bucket_arn" {
  description = "ARN S3 bucket"
  value       = aws_s3_bucket.callsum_storage.arn
}
