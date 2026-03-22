#!/bin/bash
# AWS infrastructure deployment script via Terraform

set -e  # Stop on errors

echo "🚀 DEPLOYING CALLSUM TO AWS"
echo "========================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check required tools
echo "📋 Checking dependencies..."

if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform is not installed${NC}"
    echo "Install: https://www.terraform.io/downloads"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    echo "Install: https://aws.amazon.com/cli/"
    exit 1
fi

echo -e "${GREEN}✅ All dependencies installed${NC}"
echo ""

# Build Lambda package with dependencies
echo "📦 Building Lambda package..."
"$(dirname "$0")/build_lambda_package.sh"
echo ""

# Navigate to Terraform directory
cd "$(dirname "$0")/../infrastructure/terraform"

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${YELLOW}⚠️  terraform.tfvars not found${NC}"
    echo "Create it from the example:"
    echo ""
    echo "  cp terraform.tfvars.example terraform.tfvars"
    echo "  nano terraform.tfvars  # Fill in your values"
    echo ""
    exit 1
fi

# Check AWS credentials
echo "🔐 Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Run: aws configure"
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

# Confirmation
echo ""
echo -e "${YELLOW}⚠️  WARNING: AWS infrastructure will be created${NC}"
echo ""
echo "Cost: ~\$1-3/month (S3 + Lambda + DynamoDB)"
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled by user"
    exit 0
fi

# Terraform apply
echo ""
echo "🚀 Terraform apply..."
terraform apply tfplan

# Save outputs
echo ""
echo "💾 Saving outputs..."
terraform output -json > outputs.json

# Get webhook URL
WEBHOOK_URL=$(terraform output -raw api_gateway_url)

echo ""
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 NEXT STEPS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Set Telegram Webhook:"
echo ""
echo "   curl -X POST \"https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"url\": \"${WEBHOOK_URL}\"}'"
echo ""
echo "2. Verify webhook:"
echo ""
echo "   curl \"https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo\""
echo ""
echo "3. Deploy to RunPod:"
echo ""
echo "   cd runpod_service"
echo "   ./deploy_runpod.sh"
echo ""
echo "4. Test the bot in Telegram!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Show full summary
echo "📊 SUMMARY:"
terraform output summary

echo ""
echo -e "${GREEN}🎉 Done!${NC}"
