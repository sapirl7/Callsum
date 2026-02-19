#!/bin/bash
# Скрипт деплоя ML сервиса на RunPod

set -e

echo "🚀 ДЕПЛОЙ ML СЕРВИСА НА RUNPOD"
echo "=============================="
echo ""

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Проверка зависимостей
echo "📋 Проверка зависимостей..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker не установлен${NC}"
    echo "Установите: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v runpodctl &> /dev/null; then
    echo -e "${YELLOW}⚠️  RunPod CLI не установлен${NC}"
    echo "Установка..."
    wget https://github.com/runpod/runpodctl/releases/latest/download/runpodctl-linux-amd64 -O /usr/local/bin/runpodctl
    chmod +x /usr/local/bin/runpodctl
    echo -e "${GREEN}✅ RunPod CLI установлен${NC}"
fi

echo -e "${GREEN}✅ Все зависимости установлены${NC}"
echo ""

# Переменные
DOCKER_IMAGE="callsum/ml-service"
TAG="latest"
DOCKER_REGISTRY="your-registry"  # Docker Hub или AWS ECR

# Переходим в директорию runpod_service
cd "$(dirname "$0")/../runpod_service"

# Проверка HF_TOKEN
if [ -z "$HF_TOKEN" ]; then
    echo -e "${RED}❌ Переменная HF_TOKEN не установлена${NC}"
    echo "Экспортируйте: export HF_TOKEN=your_token"
    exit 1
fi

# Билд Docker образа
echo "🐳 Сборка Docker образа..."
docker build \
    --build-arg PRELOAD_MODELS=true \
    --build-arg HF_TOKEN=$HF_TOKEN \
    -t ${DOCKER_IMAGE}:${TAG} \
    .

echo -e "${GREEN}✅ Docker образ собран${NC}"
echo ""

# Тестирование образа локально (опционально)
echo "🧪 Хотите протестировать образ локально? (yes/no)"
read -p "> " test_local

if [ "$test_local" = "yes" ]; then
    echo "Запуск контейнера для теста..."
    docker run --rm \
        --gpus all \
        -e HF_TOKEN=$HF_TOKEN \
        -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
        -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
        ${DOCKER_IMAGE}:${TAG} \
        python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())"

    echo -e "${GREEN}✅ Тест пройден${NC}"
fi

# Пуш в Docker registry
echo ""
echo "📤 Push в Docker registry..."

# Tag для registry
docker tag ${DOCKER_IMAGE}:${TAG} ${DOCKER_REGISTRY}/${DOCKER_IMAGE}:${TAG}

# Login (для Docker Hub)
echo "Логин в Docker registry..."
read -p "Docker Hub username: " DOCKER_USERNAME
docker login -u $DOCKER_USERNAME

# Push
docker push ${DOCKER_REGISTRY}/${DOCKER_IMAGE}:${TAG}

echo -e "${GREEN}✅ Образ загружен в registry${NC}"
echo ""

# Создание RunPod Serverless Endpoint
echo "🎯 Создание RunPod Serverless Endpoint..."
echo ""
echo "Перейдите на https://www.runpod.io/console/serverless"
echo ""
echo "Параметры для создания:"
echo "  - Name: callsum-ml-service"
echo "  - Docker Image: ${DOCKER_REGISTRY}/${DOCKER_IMAGE}:${TAG}"
echo "  - GPU Type: NVIDIA RTX 3090 или RTX A4000"
echo "  - Min Workers: 0 (serverless)"
echo "  - Max Workers: 1 (для начала)"
echo "  - Container Disk: 20 GB"
echo "  - Environment Variables:"
echo "    HF_TOKEN=<your_hf_token>"
echo ""
echo "После создания endpoint, скопируйте URL и API Key"
echo ""
read -p "Endpoint создан? (yes/no): " endpoint_created

if [ "$endpoint_created" != "yes" ]; then
    echo "Создайте endpoint и запустите скрипт снова"
    exit 0
fi

# Получаем endpoint URL и API Key
read -p "RunPod Endpoint URL: " RUNPOD_ENDPOINT
read -p "RunPod API Key: " RUNPOD_API_KEY

# Сохраняем в файл для Terraform
cat > ../infrastructure/terraform/runpod_config.tfvars <<EOF
runpod_endpoint_url = "$RUNPOD_ENDPOINT"
runpod_api_key = "$RUNPOD_API_KEY"
EOF

echo ""
echo -e "${GREEN}✅ Конфигурация сохранена в runpod_config.tfvars${NC}"
echo ""

# Тест endpoint
echo "🧪 Тестирование endpoint..."

RESPONSE=$(curl -s -X POST "$RUNPOD_ENDPOINT" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "test": true
    }
  }')

echo "Response: $RESPONSE"

if echo "$RESPONSE" | grep -q "error"; then
    echo -e "${RED}❌ Ошибка при тестировании endpoint${NC}"
    echo "Проверьте логи в RunPod dashboard"
else
    echo -e "${GREEN}✅ Endpoint работает!${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ ДЕПЛОЙ НА RUNPOD ЗАВЕРШЕН!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "1. Обновите Terraform с новыми RunPod credentials:"
echo "   cd ../infrastructure/terraform"
echo "   terraform apply -var-file=runpod_config.tfvars"
echo ""
echo "2. Установите Telegram webhook (если еще не установлен)"
echo ""
echo "3. Протестируйте полный цикл:"
echo "   - Отправьте голосовое в Telegram бота"
echo "   - Проверьте логи в RunPod dashboard"
echo "   - Получите результат в боте"
echo ""
echo "🎉 Готово!"
echo ""
