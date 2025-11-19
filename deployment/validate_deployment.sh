#!/bin/bash
# Pre-deployment validation script
# Проверяет конфигурацию перед деплоем

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

echo "1. Проверка зависимостей..."
echo "----------------------------"

# Check Terraform
if command_exists terraform; then
    TERRAFORM_VERSION=$(terraform version -json | python3 -c "import sys, json; print(json.load(sys.stdin)['terraform_version'])")
    success "Terraform установлен (версия: $TERRAFORM_VERSION)"
else
    error "Terraform не установлен"
fi

# Check AWS CLI
if command_exists aws; then
    AWS_VERSION=$(aws --version 2>&1 | cut -d' ' -f1 | cut -d'/' -f2)
    success "AWS CLI установлен (версия: $AWS_VERSION)"
else
    error "AWS CLI не установлен"
fi

# Check Docker
if command_exists docker; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    success "Docker установлен (версия: $DOCKER_VERSION)"
else
    warn "Docker не установлен (нужен для RunPod деплоя)"
fi

echo ""
echo "2. Проверка AWS конфигурации..."
echo "--------------------------------"

# Check AWS credentials
if aws sts get-caller-identity >/dev/null 2>&1; then
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_USER=$(aws sts get-caller-identity --query Arn --output text | cut -d'/' -f2)
    success "AWS credentials настроены (Account: $AWS_ACCOUNT, User: $AWS_USER)"
else
    error "AWS credentials не настроены. Запустите: aws configure"
fi

# Check AWS region
AWS_REGION=$(aws configure get region)
if [ -n "$AWS_REGION" ]; then
    success "AWS region установлен: $AWS_REGION"
else
    warn "AWS region не установлен. Будет использован us-east-1"
fi

echo ""
echo "3. Проверка Terraform конфигурации..."
echo "--------------------------------------"

cd "$(dirname "$0")/../infrastructure/terraform" || exit 1

# Check terraform.tfvars
if [ -f "terraform.tfvars" ]; then
    success "terraform.tfvars найден"
    
    # Check required variables
    REQUIRED_VARS=("telegram_bot_token" "hf_token" "runpod_api_key" "runpod_endpoint_url")
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}\s*=" terraform.tfvars; then
            VALUE=$(grep "^${var}\s*=" terraform.tfvars | cut -d'=' -f2 | tr -d ' "')
            if [[ "$VALUE" == "YOUR_"* ]] || [ -z "$VALUE" ]; then
                error "Переменная $var не заполнена в terraform.tfvars"
            else
                success "Переменная $var установлена"
            fi
        else
            error "Переменная $var отсутствует в terraform.tfvars"
        fi
    done
else
    error "terraform.tfvars не найден. Скопируйте terraform.tfvars.example и заполните значения"
fi

# Terraform init check
if [ -d ".terraform" ]; then
    success "Terraform инициализирован"
else
    warn "Terraform не инициализирован. Запустите: terraform init"
fi

# Terraform validate
if terraform validate >/dev/null 2>&1; then
    success "Terraform конфигурация валидна"
else
    error "Terraform конфигурация содержит ошибки"
    terraform validate
fi

echo ""
echo "4. Проверка файлов проекта..."
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
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "Найден: $file"
    else
        error "Отсутствует: $file"
    fi
done

echo ""
echo "5. Проверка Python зависимостей..."
echo "-----------------------------------"

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    success "Python установлен (версия: $PYTHON_VERSION)"
else
    error "Python 3 не установлен"
fi

# Check pip
if command_exists pip3; then
    success "pip3 установлен"
else
    error "pip3 не установлен"
fi

echo ""
echo "=================================="
echo "Результаты валидации:"
echo "=================================="

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ Найдено ошибок: $ERRORS${NC}"
    echo "Исправьте ошибки перед деплоем!"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Найдено предупреждений: $WARNINGS${NC}"
    echo "Можно продолжить деплой, но рекомендуется исправить предупреждения"
    exit 0
else
    echo -e "${GREEN}✅ Все проверки пройдены успешно!${NC}"
    echo "Готово к деплою!"
    exit 0
fi
