# S3 Bucket для хранения аудио и результатов
# Создается только если НЕ используется DigitalOcean Spaces

resource "aws_s3_bucket" "callsum_storage" {
  count  = var.use_digitalocean_spaces ? 0 : 1
  bucket = var.s3_bucket_name

  tags = merge(local.common_tags, {
    Name = "Callsum Audio & Results Storage"
  })
}

# Включаем версионирование
resource "aws_s3_bucket_versioning" "callsum_storage" {
  count  = var.use_digitalocean_spaces ? 0 : 1
  bucket = aws_s3_bucket.callsum_storage[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

# Включаем шифрование по умолчанию (AES-256)
resource "aws_s3_bucket_server_side_encryption_configuration" "callsum_storage" {
  count  = var.use_digitalocean_spaces ? 0 : 1
  bucket = aws_s3_bucket.callsum_storage[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Блокируем публичный доступ
resource "aws_s3_bucket_public_access_block" "callsum_storage" {
  count  = var.use_digitalocean_spaces ? 0 : 1
  bucket = aws_s3_bucket.callsum_storage[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle правила для автоудаления старых файлов
resource "aws_s3_bucket_lifecycle_configuration" "callsum_storage" {
  count  = var.use_digitalocean_spaces ? 0 : 1
  bucket = aws_s3_bucket.callsum_storage[0].id

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


# Outputs
output "s3_bucket_name" {
  description = "Имя S3 bucket (или DigitalOcean Space)"
  value       = var.use_digitalocean_spaces ? var.s3_bucket_name : aws_s3_bucket.callsum_storage[0].id
}

output "s3_bucket_arn" {
  description = "ARN S3 bucket (только для AWS S3)"
  value       = var.use_digitalocean_spaces ? "N/A (using DigitalOcean Spaces)" : aws_s3_bucket.callsum_storage[0].arn
}
