# S3 Bucket for audio and results storage
# Created only if DigitalOcean Spaces is NOT used

resource "aws_s3_bucket" "callsum_storage" {
  count  = var.use_digitalocean_spaces ? 0 : 1
  bucket = var.s3_bucket_name

  tags = merge(local.common_tags, {
    Name = "Callsum Audio & Results Storage"
  })
}

# Enable versioning
resource "aws_s3_bucket_versioning" "callsum_storage" {
  count  = var.use_digitalocean_spaces ? 0 : 1
  bucket = aws_s3_bucket.callsum_storage[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable default encryption (AES-256)
resource "aws_s3_bucket_server_side_encryption_configuration" "callsum_storage" {
  count  = var.use_digitalocean_spaces ? 0 : 1
  bucket = aws_s3_bucket.callsum_storage[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "callsum_storage" {
  count  = var.use_digitalocean_spaces ? 0 : 1
  bucket = aws_s3_bucket.callsum_storage[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle rules for automatic cleanup of old files
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
      days = 30  # Delete audio older than 30 days
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
      days = 90  # Keep results for 90 days
    }
  }
}


# Outputs
output "s3_bucket_name" {
  description = "S3 bucket name (or DigitalOcean Space name)"
  value       = var.use_digitalocean_spaces ? var.s3_bucket_name : aws_s3_bucket.callsum_storage[0].id
}

output "s3_bucket_arn" {
  description = "S3 bucket ARN (AWS S3 only)"
  value       = var.use_digitalocean_spaces ? "N/A (using DigitalOcean Spaces)" : aws_s3_bucket.callsum_storage[0].arn
}
