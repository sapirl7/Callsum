#!/bin/bash
# Скрипт деплоя AWS инфраструктуры через Terraform

set -e  # Останавливаемся при ошибках

echo "🚀 ДЕПЛОЙ CALLSUM НА AWS"
echo "========================"
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Проверка необходимых инструментов
echo "📋 Проверка зависимостей..."

if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform не установлен${NC}"
    echo "Установите: https://www.terraform.io/downloads"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI не установлен${NC}"
    echo "Установите: https://aws.amazon.com/cli/"
    exit 1
fi

echo -e "${GREEN}✅ Все зависимости установлены${NC}"
echo ""

# Переходим в директорию Terraform
cd "$(dirname "$0")/../infrastructure/terraform"

# Проверка наличия terraform.tfvars
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${YELLOW}⚠️  Файл terraform.tfvars не найден${NC}"
    echo "Создайте его на основе terraform.tfvars.example:"
    echo ""
    echo "  cp terraform.tfvars.example terraform.tfvars"
    echo "  nano terraform.tfvars  # И заполните своими значениями"
    echo ""
    exit 1
fi

# Проверка AWS credentials
echo "🔐 Проверка AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials не настроены${NC}"
    echo "Настройте: aws configure"
    exit 1
fi

AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
echo -e "${GREEN}✅ AWS Account: ${AWS_ACCOUNT}${NC}"
echo -e "${GREEN}✅ AWS Region: ${AWS_REGION}${NC}"
echo ""

# Terraform init
echo "🔧 Terraform init..."
terraform init

# Terraform validate
echo "✅ Terraform validate..."
terraform validate

# Terraform plan
echo "📊 Terraform plan..."
terraform plan -out=tfplan

# Подтверждение
echo ""
echo -e "${YELLOW}⚠️  ВНИМАНИЕ: Сейчас будет создана инфраструктура на AWS${NC}"
echo ""
echo "Стоимость: ~\$1-3/месяц (S3 + Lambda + DynamoDB + SQS)"
echo ""
read -p "Продолжить? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Отменено пользователем"
    exit 0
fi

# Terraform apply
echo ""
echo "🚀 Terraform apply..."
terraform apply tfplan

# Сохраняем outputs
echo ""
echo "💾 Сохранение outputs..."
terraform output -json > outputs.json

# Получаем webhook URL
WEBHOOK_URL=$(terraform output -raw api_gateway_url)

echo ""
echo -e "${GREEN}✅ ДЕПЛОЙ ЗАВЕРШЕН!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 СЛЕДУЮЩИЕ ШАГИ:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Установите Telegram Webhook:"
echo ""
echo "   curl -X POST \"https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"url\": \"${WEBHOOK_URL}\"}'"
echo ""
echo "2. Проверьте webhook:"
echo ""
echo "   curl \"https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo\""
echo ""
echo "3. Деплой на RunPod:"
echo ""
echo "   cd runpod_service"
echo "   ./deploy_runpod.sh"
echo ""
echo "4. Тестируйте бота в Telegram!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Показываем полную сводку
echo "📊 СВОДКА:"
terraform output summary

echo ""
echo -e "${GREEN}🎉 Готово!${NC}"
