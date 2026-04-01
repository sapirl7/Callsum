# Callsum AWS Infrastructure - Main Configuration
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.38"
    }
  }

  # Backend for state storage (uncomment after creating the bucket)
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

# Local variables
locals {
  project_name = "callsum"
  common_tags = {
    Project     = "Callsum"
    Environment = var.environment
  }
}
