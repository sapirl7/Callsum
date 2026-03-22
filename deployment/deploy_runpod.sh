#!/bin/bash
# ML service deployment script for RunPod

set -euo pipefail

echo "🚀 DEPLOYING ML SERVICE TO RUNPOD"
echo "=============================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "📋 Checking dependencies..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Install: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo -e "${RED}❌ curl is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All dependencies installed${NC}"
echo ""

if [ -z "${HF_TOKEN:-}" ]; then
    echo -e "${RED}❌ HF_TOKEN environment variable is not set${NC}"
    echo "Export it: export HF_TOKEN=your_token"
    exit 1
fi

cd "$(dirname "$0")/../runpod_service"

TAG="${TAG:-latest}"
IMAGE_NAME="${IMAGE_NAME:-callsum-ml-service}"

read -p "Docker Hub username or registry namespace: " DOCKER_NAMESPACE
if [ -z "$DOCKER_NAMESPACE" ]; then
    echo -e "${RED}❌ Namespace not specified${NC}"
    exit 1
fi

FULL_IMAGE="${DOCKER_NAMESPACE}/${IMAGE_NAME}:${TAG}"

echo ""
echo "🐳 Building Docker image..."
docker build \
    --platform linux/amd64 \
    --build-arg PRELOAD_MODELS=true \
    --build-arg HF_TOKEN="$HF_TOKEN" \
    -t "$FULL_IMAGE" \
    .

echo -e "${GREEN}✅ Docker image built: ${FULL_IMAGE}${NC}"
echo ""

read -p "Test image locally (yes/no)? " test_local
if [ "$test_local" = "yes" ]; then
    docker run --rm --entrypoint python3 "$FULL_IMAGE" -c "import torch; print('CUDA available:', torch.cuda.is_available())"
fi

echo ""
echo "📤 Pushing to Docker Hub / registry..."
docker login
docker push "$FULL_IMAGE"

echo -e "${GREEN}✅ Image pushed: ${FULL_IMAGE}${NC}"
echo ""

echo "🎯 Creating RunPod Serverless Endpoint"
echo "Go to https://www.runpod.io/console/serverless"
echo ""
echo "Parameters:"
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

read -p "Endpoint created? (yes/no): " endpoint_created
if [ "$endpoint_created" != "yes" ]; then
    echo "Create the endpoint and run this script again"
    exit 0
fi

read -p "RunPod Endpoint URL (without /run): " RUNPOD_ENDPOINT
read -p "RunPod API Key: " RUNPOD_API_KEY

TFVARS_FILE="../infrastructure/terraform/runpod.auto.tfvars"
cat > "$TFVARS_FILE" <<EOF
runpod_endpoint_url = "$RUNPOD_ENDPOINT"
runpod_api_key = "$RUNPOD_API_KEY"
EOF

echo ""
echo -e "${GREEN}✅ Configuration saved to ${TFVARS_FILE}${NC}"
echo ""

echo "🧪 Testing endpoint..."
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
    echo -e "${RED}❌ Error testing endpoint${NC}"
    echo "Check logs in RunPod dashboard"
    exit 1
fi

echo -e "${GREEN}✅ Endpoint is responding${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ RUNPOD DEPLOYMENT COMPLETE!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "1. Navigate to ../infrastructure/terraform"
echo "2. Run terraform apply"
echo "3. Verify Telegram webhook and full processing cycle"
