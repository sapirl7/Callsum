# Callsum AWS Infrastructure - Main Configuration
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend для хранения state (раскомментируйте после создания bucket)
  # backend "s3" {
  #   bucket         = "callsum-terraform-state"
  #   key            = "prod/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Callsum"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Локальные переменные
locals {
  project_name = "callsum"
  common_tags = {
    Project     = "Callsum"
    Environment = var.environment
  }
}
