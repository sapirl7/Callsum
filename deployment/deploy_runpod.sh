#!/bin/bash
# Скрипт деплоя ML сервиса на RunPod

set -euo pipefail

echo "🚀 ДЕПЛОЙ ML СЕРВИСА НА RUNPOD"
echo "=============================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "📋 Проверка зависимостей..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker не установлен${NC}"
    echo "Установите: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo -e "${RED}❌ curl не установлен${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Все зависимости установлены${NC}"
echo ""

if [ -z "${HF_TOKEN:-}" ]; then
    echo -e "${RED}❌ Переменная HF_TOKEN не установлена${NC}"
    echo "Экспортируйте: export HF_TOKEN=your_token"
    exit 1
fi

cd "$(dirname "$0")/../runpod_service"

TAG="${TAG:-latest}"
IMAGE_NAME="${IMAGE_NAME:-callsum-ml-service}"

read -p "Docker Hub username или namespace registry: " DOCKER_NAMESPACE
if [ -z "$DOCKER_NAMESPACE" ]; then
    echo -e "${RED}❌ Namespace не указан${NC}"
    exit 1
fi

FULL_IMAGE="${DOCKER_NAMESPACE}/${IMAGE_NAME}:${TAG}"

echo ""
echo "🐳 Сборка Docker образа..."
docker build \
    --platform linux/amd64 \
    --build-arg PRELOAD_MODELS=true \
    --build-arg HF_TOKEN="$HF_TOKEN" \
    -t "$FULL_IMAGE" \
    .

echo -e "${GREEN}✅ Docker образ собран: ${FULL_IMAGE}${NC}"
echo ""

read -p "Протестировать образ локально (yes/no)? " test_local
if [ "$test_local" = "yes" ]; then
    docker run --rm --entrypoint python3 "$FULL_IMAGE" -c "import torch; print('CUDA available:', torch.cuda.is_available())"
fi

echo ""
echo "📤 Push в Docker Hub / registry..."
docker login
docker push "$FULL_IMAGE"

echo -e "${GREEN}✅ Образ загружен: ${FULL_IMAGE}${NC}"
echo ""

echo "🎯 Создание RunPod Serverless Endpoint"
echo "Перейдите на https://www.runpod.io/console/serverless"
echo ""
echo "Параметры:"
echo "  - Name: callsum-ml-service"
echo "  - Docker Image: ${FULL_IMAGE}"
echo "  - Endpoint Type: Queue"
echo "  - GPU Type: NVIDIA RTX 3090 / RTX 4090 / A4000"
echo "  - Min Workers: 0"
echo "  - Max Workers: 1"
echo "  - Container Disk: 20 GB"
echo "  - Environment Variables:"
echo "      HF_TOKEN=<your_hf_token>"
echo ""

read -p "Endpoint создан? (yes/no): " endpoint_created
if [ "$endpoint_created" != "yes" ]; then
    echo "Создайте endpoint и запустите скрипт снова"
    exit 0
fi

read -p "RunPod Endpoint URL (без /run): " RUNPOD_ENDPOINT
read -p "RunPod API Key: " RUNPOD_API_KEY

TFVARS_FILE="../infrastructure/terraform/runpod.auto.tfvars"
cat > "$TFVARS_FILE" <<EOF
runpod_endpoint_url = "$RUNPOD_ENDPOINT"
runpod_api_key = "$RUNPOD_API_KEY"
EOF

echo ""
echo -e "${GREEN}✅ Конфигурация сохранена в ${TFVARS_FILE}${NC}"
echo ""

echo "🧪 Тестирование endpoint..."
RESPONSE=$(curl -sS -X POST "${RUNPOD_ENDPOINT}/run" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "test": true
    }
  }')

echo "Response: $RESPONSE"

if echo "$RESPONSE" | grep -q '"status":"error"\|"error"'; then
    echo -e "${RED}❌ Ошибка при тестировании endpoint${NC}"
    echo "Проверьте логи в RunPod dashboard"
    exit 1
fi

echo -e "${GREEN}✅ Endpoint отвечает${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ ДЕПЛОЙ НА RUNPOD ЗАВЕРШЕН!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Следующие шаги:"
echo "1. Перейдите в ../infrastructure/terraform"
echo "2. Выполните terraform apply"
echo "3. Проверьте Telegram webhook и полный цикл обработки"
