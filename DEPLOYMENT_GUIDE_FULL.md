<![CDATA[# 🚀 Callsum — Full Deployment Walkthrough

> **Status:** Extended long-form deployment guide.
> For handoff and final acceptance, use `docs/HANDOFF_CHECKLIST.md` and `docs/PROJECT_STATUS.md`.

## Architecture Overview

**Callsum** uses a hybrid cloud architecture:
- **AWS** — Telegram bot, storage, database (lightweight ops)
- **RunPod** — ML processing on GPU (heavy compute)

### What you'll need:

1. **AWS account** (~$2–5/month)
2. **RunPod account** (~$10–15/month with active usage)
3. **Telegram Bot Token** (free)
4. **Hugging Face Token** (free)
5. **Docker Desktop** (for building the image)
6. **Terraform** (for automated deployment)

---

## 📋 PART 1: Preparation (30 minutes)

### 1.1 Create an AWS account

1. Go to https://aws.amazon.com
2. Click **Create an AWS Account**
3. Fill in: email, password, account name (e.g., "callsum-production")
4. Link a payment card ($1 verification charge)
5. Select the **Free Tier** plan

### 1.2 Install AWS CLI

```bash
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Verify
aws --version
```

### 1.3 Create AWS Access Keys

1. Log in to AWS Console → click your name → **Security credentials**
2. Scroll to **Access keys** → **Create access key**
3. Select **Command Line Interface (CLI)**
4. Save both the Access key ID and Secret access key

```bash
aws configure
# AWS Access Key ID: <your key>
# AWS Secret Access Key: <your secret>
# Default region: us-east-1
# Default output format: json
```

### 1.4 Create a Telegram bot

1. Open Telegram → find **@BotFather**
2. Send `/newbot` → follow the instructions
3. Save the token (e.g., `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 1.5 Get a Hugging Face Token

1. Go to https://huggingface.co → **Settings** → **Access Tokens** → **New token** (Read)
2. Save the token

### 1.6 Sign up for RunPod

1. Go to https://www.runpod.io → **Sign Up**
2. Add funds ($10 minimum recommended)

### 1.7 Install Terraform

```bash
# macOS
brew install hashicorp/tap/terraform

# Linux
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Verify
terraform --version
```

### 1.8 Install Docker Desktop

- **macOS/Windows:** download from https://www.docker.com/products/docker-desktop/
- **Linux:** `curl -fsSL https://get.docker.com | sh`
- Verify: `docker --version`

---

## 📦 PART 2: Deploy AWS Infrastructure (20 minutes)

### 2.1 Clone the project

```bash
git clone https://github.com/sapirl7/Callsum.git
cd Callsum
```

### 2.2 Configure Terraform variables

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars
```

Fill in all values:
```hcl
aws_region  = "us-east-1"
environment = "prod"

telegram_bot_token  = "123456:ABC-DEF..."
telegram_secret_token = "$(openssl rand -hex 32)"  # Generate with: openssl rand -hex 32

hf_token = "hf_ABC..."

# Temporary — update after RunPod endpoint creation
runpod_api_key      = "TEMP"
runpod_endpoint_url = "https://api.runpod.ai/v2/TEMP"

s3_bucket_name = "callsum-prod-<YOUR-UNIQUE-ID>"

alert_email          = "your@email.com"
monthly_budget_limit = 25
```

### 2.3 Deploy

```bash
terraform init
terraform validate
terraform plan
terraform apply  # Enter: yes (takes ~5–7 minutes)
```

Save the `webhook_url` from the output.

### 2.4 Package Lambda code

```bash
cd ../../deployment
./build_lambda_package.sh
cd ../infrastructure/terraform
terraform apply
```

---

## 🐳 PART 3: Deploy ML Service on RunPod (30 minutes)

### 3.1 Create a RunPod Serverless Endpoint

1. Go to https://www.runpod.io/console/serverless → **+ New Endpoint**
2. Fill in:
   - **Name:** `callsum-ml-service`
   - **GPU Type:** RTX 3090 (24 GB VRAM) or RTX 4090
   - **Min Workers:** 0 (serverless)
   - **Max Workers:** 1
   - **Container Disk:** 20 GB
3. **Environment Variables:** `HF_TOKEN=hf_...`
4. Click **Create** and save the Endpoint ID + API Key

### 3.2 Build the Docker image

```bash
cd runpod_service
export HF_TOKEN=hf_...

docker build \
  --build-arg PRELOAD_MODELS=true \
  --build-arg HF_TOKEN=$HF_TOKEN \
  -t callsum-ml:latest .
```

⏱ Build time: ~30–40 minutes (downloads Whisper + Llama 3.1 models)

### 3.3 Push to Docker Hub

```bash
docker login
docker tag callsum-ml:latest <your-username>/callsum-ml:latest
docker push <your-username>/callsum-ml:latest
```

### 3.4 Update RunPod endpoint settings

Set the Docker Image to `<your-username>/callsum-ml:latest`.

### 3.5 Update Terraform with RunPod credentials

```bash
cd ../../infrastructure/terraform
nano terraform.tfvars
# Update: runpod_api_key and runpod_endpoint_url
terraform apply
```

---

## 🔗 PART 4: Configure Telegram Webhook (5 minutes)

```bash
WEBHOOK_URL=$(terraform output -raw api_gateway_url)

curl -X POST "https://api.telegram.org/bot<YOUR-BOT-TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$WEBHOOK_URL\", \"secret_token\": \"<your-secret-token>\"}"

# Verify
curl "https://api.telegram.org/bot<YOUR-BOT-TOKEN>/getWebhookInfo"
```

---

## ✅ PART 5: Testing (10 minutes)

1. Open Telegram → find your bot → send `/start`
2. Record a 30–60 second voice message → send it
3. Wait for the result (~2–3 minutes)
4. Check CloudWatch Logs: `aws logs tail /aws/lambda/callsum-telegram-bot-prod --follow`

---

## 📊 PART 6: Monitoring

- **CloudWatch Dashboard:** AWS Console → CloudWatch → Dashboards → `callsum-monitoring-prod`
- **Cost Explorer:** AWS Console → Cost Management → filter by `Project: Callsum`
- **Budget Alerts:** Email notifications at 50%, 80%, 100% of budget

---

## 🛠 PART 7: Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot does not respond | Check webhook (`getWebhookInfo`), check Lambda logs |
| Rate limit exceeded | Wait 1 hour, or increase in `terraform.tfvars` |
| GPU timeout | Split audio into shorter parts, or increase timeout |
| Out of memory | Switch to RTX 4090 or A40 in RunPod |
| Webhook not working | Verify `secret_token` matches, reinstall webhook |

---

## 🔄 PART 8: Updating

```bash
# Update Lambda code
./deployment/build_lambda_package.sh && cd infrastructure/terraform && terraform apply

# Update RunPod image
cd runpod_service && docker build -t callsum-ml . && docker push <username>/callsum-ml:latest

# Update infrastructure
cd infrastructure/terraform && terraform apply
```

---

## 🗑 PART 9: Teardown

```bash
cd infrastructure/terraform
terraform destroy  # Enter: yes
# Then manually delete the RunPod endpoint
```

⚠️ This will delete all data in S3, DynamoDB, Lambda, API Gateway, and Secrets Manager.
]]>
