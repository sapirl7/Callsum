<![CDATA[# 📚 Callsum — Full Deployment Guide

> This is the primary detailed deployment guide.
> For client handoff, supplement with `docs/HANDOFF_CHECKLIST.md` and `docs/PROJECT_STATUS.md`.

This guide walks you through the entire process of deploying Callsum — from zero to a fully working system.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Service Registration](#registration)
3. [Local Setup](#local-setup)
4. [AWS Infrastructure Deployment](#aws-deployment)
5. [RunPod ML Service Deployment](#runpod-deployment)
6. [Telegram Bot Setup](#telegram-setup)
7. [Testing](#testing)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)

---

## <a name="prerequisites"></a>1️⃣ Prerequisites

### Install the tools:

1. **Git**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install git

   # macOS
   brew install git
   ```

2. **Docker**
   - Download: https://docs.docker.com/get-docker/
   - Verify: `docker --version`

3. **Terraform**
   ```bash
   # Ubuntu/Debian
   wget https://releases.hashicorp.com/terraform/1.6.6/terraform_1.6.6_linux_amd64.zip
   unzip terraform_1.6.6_linux_amd64.zip
   sudo mv terraform /usr/local/bin/

   # macOS
   brew install terraform
   ```
   - Verify: `terraform --version`

4. **AWS CLI**
   ```bash
   # Ubuntu/Debian
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install

   # macOS
   brew install awscli
   ```
   - Verify: `aws --version`

---

## <a name="registration"></a>2️⃣ Service Registration

### 2.1 AWS

1. Create an account: https://aws.amazon.com/
2. Set up an IAM user with permissions:
   - AmazonS3FullAccess
   - AmazonDynamoDBFullAccess
   - AWSLambdaFullAccess
   - AmazonAPIGatewayAdministrator
   - SecretsManagerReadWrite
3. Obtain an Access Key ID and Secret Access Key
4. Configure AWS CLI:
   ```bash
   aws configure
   # AWS Access Key ID: <your key>
   # AWS Secret Access Key: <your secret>
   # Default region: us-east-1
   # Default output format: json
   ```

### 2.2 RunPod

1. Sign up: https://www.runpod.io/console/signup
2. Add funds ($10 minimum)
3. Get an API Key:
   - Settings → API Keys → Create API Key
   - Save the key!

### 2.3 Hugging Face

1. Sign up: https://huggingface.co/join
2. Get a token:
   - Settings → Access Tokens → New token
   - Type: Read
   - Save the token!

### 2.4 Telegram Bot

1. Open Telegram and search for @BotFather
2. Send `/newbot`
3. Follow the instructions
4. Save the Bot Token (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

---

## <a name="local-setup"></a>3️⃣ Local Setup

### 3.1 Clone the repository

```bash
git clone https://github.com/sapirl7/Callsum.git
cd Callsum
```

### 3.2 Configure Terraform variables

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars
```

Fill in the values:
```hcl
# AWS
aws_region  = "us-east-1"
environment = "prod"

# Telegram
telegram_bot_token = "123456:ABC-DEF..."  # Your token

# Hugging Face
hf_token = "hf_..."  # Your token

# RunPod (fill in after creating the endpoint)
runpod_api_key      = "leave-empty-for-now"
runpod_endpoint_url = "leave-empty-for-now"

# S3 (the name must be globally unique!)
s3_bucket_name      = "callsum-prod-YOUR-UNIQUE-ID"
dynamodb_table_name = "callsum-jobs"
```

---

## <a name="aws-deployment"></a>4️⃣ AWS Infrastructure Deployment

### 4.1 Automated deployment

```bash
cd deployment
./deploy_aws.sh
```

The script will:
- ✅ Check dependencies
- ✅ Run terraform init, validate, plan
- ✅ Create infrastructure (after your confirmation)
- ✅ Display summary information

### 4.2 Manual deployment (alternative)

```bash
cd infrastructure/terraform

# Initialize
terraform init

# Validate configuration
terraform validate

# Review the plan
terraform plan

# Apply (create infrastructure)
terraform apply

# Save outputs
terraform output -json > outputs.json
```

### 4.3 What gets created?

- **S3 Bucket** — audio and result storage (AES-256 encryption)
- **DynamoDB Table** — job metadata and rate limiting
- **Lambda Function** — Telegram bot
- **API Gateway** — webhook for Telegram
- **Secrets Manager** — token storage
- **IAM Roles** — access permissions
- **CloudWatch** — logs and metrics

### 4.4 Cost

Approximately **$1–3/month** at 60 hours of audio/month:
- S3: ~$1
- Lambda: ~$0.50
- DynamoDB: ~$0.30
- API Gateway: ~$0.10

---

## <a name="runpod-deployment"></a>5️⃣ RunPod ML Service Deployment

### 5.1 Build the Docker image

```bash
cd runpod_service

# Export HF_TOKEN
export HF_TOKEN=your_hf_token_here

# Build the Docker image
docker build -t callsum/ml-service:latest .
```

### 5.2 Push to Docker Registry

**Option A: Docker Hub**

```bash
# Login
docker login -u YOUR_USERNAME

# Tag
docker tag callsum/ml-service:latest YOUR_USERNAME/callsum-ml-service:latest

# Push
docker push YOUR_USERNAME/callsum-ml-service:latest
```

**Option B: AWS ECR**

```bash
# Create ECR repository
aws ecr create-repository --repository-name callsum-ml-service

# Get login command
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag callsum/ml-service:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/callsum-ml-service:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/callsum-ml-service:latest
```

### 5.3 Create a RunPod Serverless Endpoint

1. Go to https://www.runpod.io/console/serverless
2. Click **"+ New Endpoint"**
3. Fill in:
   - **Name**: `callsum-ml-service`
   - **Docker Image**: `YOUR_USERNAME/callsum-ml-service:latest`
   - **GPU Type**: NVIDIA RTX 3090 ($0.44/hr)
   - **Container Disk**: 20 GB
   - **Min Workers**: 0 (serverless — pay only for usage)
   - **Max Workers**: 1 (to start)
   - **Idle Timeout**: 5 minutes

4. **Environment Variables**:
   ```
   HF_TOKEN=your_hf_token
   ```

5. Click **"Deploy"**

6. Copy:
   - **Endpoint ID**
   - **API Key**

### 5.4 Update Terraform

```bash
cd infrastructure/terraform
nano terraform.tfvars
```

Add:
```hcl
runpod_api_key      = "YOUR_RUNPOD_API_KEY"
runpod_endpoint_url = "https://api.runpod.ai/v2/ENDPOINT_ID/run"
```

Apply changes:
```bash
terraform apply
```

---

## <a name="telegram-setup"></a>6️⃣ Telegram Bot Setup

### 6.1 Get the Webhook URL

```bash
cd infrastructure/terraform
WEBHOOK_URL=$(terraform output -raw api_gateway_url)
echo $WEBHOOK_URL
```

### 6.2 Set the Webhook

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$WEBHOOK_URL\"}"
```

Expected response:
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

### 6.3 Verify the Webhook

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

Expected:
```json
{
  "ok": true,
  "result": {
    "url": "YOUR_WEBHOOK_URL",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

---

## <a name="testing"></a>7️⃣ Testing

### 7.1 Basic test

1. Open Telegram
2. Find your bot (by username)
3. Send `/start`

### 7.2 Audio processing test

1. Record a voice message (10–30 seconds)
2. Send it to the bot
3. Wait for the result (~1–2 minutes for short audio)

### 7.3 Check logs

**AWS CloudWatch:**
```bash
aws logs tail /aws/lambda/callsum-telegram-bot-prod --follow
```

**RunPod Dashboard:**
- Go to https://www.runpod.io/console/serverless
- Select your endpoint
- Navigate to "Logs"

---

## <a name="monitoring"></a>8️⃣ Monitoring

### 8.1 CloudWatch Dashboards

Metrics to track:
- Lambda errors
- Lambda duration
- DynamoDB throttles
- API Gateway 4xx/5xx
- RunPod job success rate

### 8.2 Cost Explorer

Track costs at:
- https://console.aws.amazon.com/cost-management/home

### 8.3 RunPod Analytics

- https://www.runpod.io/console/serverless
- "Analytics" tab
- Metrics: execution time, cold starts, costs

---

## <a name="troubleshooting"></a>9️⃣ Troubleshooting

### Problem: Bot does not respond

1. Check webhook:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
   ```
2. Check Lambda logs:
   ```bash
   aws logs tail /aws/lambda/callsum-telegram-bot-prod --follow
   ```
3. Check API Gateway:
   - AWS Console → API Gateway → callsum-telegram-webhook-prod → Logs

### Problem: RunPod does not start

1. Test the Docker image locally:
   ```bash
   docker run --gpus all -e HF_TOKEN=$HF_TOKEN callsum/ml-service:latest
   ```
2. Check RunPod logs: Console → Endpoint → Logs
3. Verify environment variables in RunPod

### Problem: "S3 Access Denied"

1. Verify the Lambda IAM role:
   ```bash
   aws iam get-role-policy --role-name callsum-lambda-telegram-bot-prod --policy-name callsum-lambda-telegram-bot-policy
   ```
2. Check the S3 bucket policy:
   ```bash
   aws s3api get-bucket-policy --bucket callsum-prod
   ```

### Problem: High costs

1. Check RunPod Idle Timeout (should be 5 min)
2. Verify S3 Lifecycle rules (auto-delete old files)
3. Reduce Lambda memory if unused

---

## 🎉 Done!

Your Callsum instance is deployed and ready!

**Useful links:**
- AWS Console: https://console.aws.amazon.com/
- RunPod Console: https://www.runpod.io/console
- Telegram Bot API: https://core.telegram.org/bots/api

**Cost:** ~$10–15/month at 60 hours of audio
**Processing time:** ~20 minutes per 1 hour of audio
**Security:** ✅ Encryption, ✅ Isolation, ✅ Least privilege
]]>
