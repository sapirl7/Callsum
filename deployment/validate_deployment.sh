#!/bin/bash
# Pre-deployment validation script
# Checks configuration before deployment

set -e

echo "🔍 Callsum Deployment Validation"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function for error messages
error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
    ((ERRORS++))
}

# Function for warning messages
warn() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
    ((WARNINGS++))
}

# Function for success messages
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

echo "1. Checking dependencies..."
echo "----------------------------"

# Check Terraform
if command_exists terraform; then
    TERRAFORM_VERSION=$(terraform version -json | python3 -c "import sys, json; print(json.load(sys.stdin)['terraform_version'])")
    success "Terraform installed (version: $TERRAFORM_VERSION)"
else
    error "Terraform is not installed"
fi

# Check AWS CLI
if command_exists aws; then
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1 | cut -d'/' -f2)
    success "AWS CLI installed (version: $AWS_VERSION)"
else
    error "AWS CLI is not installed"
fi

# Check Docker
if command_exists docker; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    success "Docker installed (version: $DOCKER_VERSION)"
else
    warn "Docker is not installed (required for RunPod deployment)"
fi

echo ""
echo "2. Checking AWS configuration..."
echo "--------------------------------"

# Check AWS credentials
if aws sts get-caller-identity >/dev/null 2>&1; then
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_USER=$(aws sts get-caller-identity --query Arn --output text | cut -d'/' -f2)
    success "AWS credentials configured (Account: $AWS_ACCOUNT, User: $AWS_USER)"
else
    error "AWS credentials not configured. Run: aws configure"
fi

# Check AWS region
AWS_REGION=$(aws configure get region)
if [ -n "$AWS_REGION" ]; then
    success "AWS region set: $AWS_REGION"
else
    warn "AWS region not set. Will use us-east-1"
fi

echo ""
echo "3. Checking Terraform configuration..."
echo "--------------------------------------"

cd "$(dirname "$0")/../infrastructure/terraform" || exit 1

# Check terraform.tfvars
if [ -f "terraform.tfvars" ]; then
    success "terraform.tfvars found"
    
    # Check required variables
    REQUIRED_VARS=("telegram_bot_token" "hf_token" "runpod_api_key" "runpod_endpoint_url")
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}\s*=" terraform.tfvars; then
            VALUE=$(grep "^${var}\s*=" terraform.tfvars | cut -d'=' -f2 | tr -d ' "')
            if [[ "$VALUE" == "YOUR_"* ]] || [ -z "$VALUE" ]; then
                error "Variable $var is not set in terraform.tfvars"
            else
                success "Variable $var is set"
            fi
        else
            error "Variable $var is missing from terraform.tfvars"
        fi
    done
else
    error "terraform.tfvars not found. Copy terraform.tfvars.example and fill in the values"
fi

# Terraform init check
if [ -d ".terraform" ]; then
    success "Terraform initialized"
else
    warn "Terraform not initialized. Run: terraform init"
fi

# Terraform validate
if terraform validate >/dev/null 2>&1; then
    success "Terraform configuration is valid"
else
    error "Terraform configuration contains errors"
    terraform validate
fi

echo ""
echo "4. Checking project files..."
echo "------------------------------"

cd "$(dirname "$0")/.." || exit 1

# Check required files
REQUIRED_FILES=(
    "requirements.txt"
    "telegram_bot/bot.py"
    "telegram_bot/requirements.txt"
    "runpod_service/handler.py"
    "runpod_service/requirements.txt"
    "runpod_service/Dockerfile"
    "config.py"
    "deployment/build_lambda_package.sh"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "Found: $file"
    else
        error "Missing: $file"
    fi
done

if [ -d "telegram_bot/build/lambda" ]; then
    success "Lambda build directory found: telegram_bot/build/lambda"
else
    warn "Lambda build directory missing. Run: ./deployment/build_lambda_package.sh"
fi

echo ""
echo "5. Checking Python dependencies..."
echo "-----------------------------------"

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    success "Python installed (version: $PYTHON_VERSION)"
else
    error "Python 3 is not installed"
fi

# Check pip
if command_exists pip3; then
    success "pip3 installed"
else
    error "pip3 is not installed"
fi

echo ""
echo "=================================="
echo "Validation results:"
echo "=================================="

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ Errors found: $ERRORS${NC}"
    echo "Fix errors before deployment!"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Warnings found: $WARNINGS${NC}"
    echo "You can proceed with deployment, but it is recommended to fix warnings"
    exit 0
else
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo "Ready to deploy!"
    exit 0
fi
