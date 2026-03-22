# ⚡ Callsum — Quick Start

> **Status:** Supplementary quick-start guide.
> **Canonical handoff documents:** `docs/HANDOFF_CHECKLIST.md`, `docs/PROJECT_STATUS.md`, `docs/DEPLOYMENT_GUIDE.md`.

## What Is This?

**Callsum** is an AI-powered audio analysis service:
- 🎙️ Transcription (Whisper large-v3)
- 👥 Speaker identification (Pyannote 3.1)
- 📝 Smart summaries (Llama 3.1 8B Instruct)
- 📱 Telegram bot interface

---

## 💰 Cost

| Setup | AWS | RunPod GPU | Total |
|-------|-----|-----------|-------|
| Full AWS | ~$2–5/mo | ~$10–15/mo | **$12–20/mo** |
| AWS + DO Spaces | ~$2–3/mo + $5/mo DO | ~$10–15/mo | **$17–23/mo** |

---

## 🚀 Quick Start (30 min)

### 1. Create accounts

| Service | Purpose | Link | Cost |
|---------|---------|------|------|
| **AWS** | Bot + DB | [aws.amazon.com](https://aws.amazon.com) | ~$2/mo |
| **RunPod** | GPU processing | [runpod.io](https://runpod.io) | ~$10–15/mo |
| **Telegram** | Bot interface | [@BotFather](https://t.me/BotFather) | Free |
| **Hugging Face** | ML models | [huggingface.co](https://huggingface.co) | Free |

**Optional:** DigitalOcean for storage ($5/mo) — see [DO Spaces Guide](docs/DIGITALOCEAN_SPACES_GUIDE.md).

### 2. Get tokens

```bash
# 1. Telegram Bot Token — @BotFather → /newbot
# 2. Hugging Face Token — huggingface.co → Settings → Access Tokens → New (Read)
# 3. AWS Access Keys — AWS Console → IAM → Users → Security credentials → Create access key
# 4. RunPod API Key — runpod.io → Settings → API Keys → Create
```

### 3. Install tools

```bash
brew install terraform awscli  # macOS
# Docker: https://www.docker.com/products/docker-desktop/

aws configure
# Enter Access Key ID and Secret Access Key
```

### 4. Configure

```bash
git clone https://github.com/sapirl7/Callsum.git
cd Callsum/infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Fill in your tokens
```

### 5. Deploy AWS

```bash
terraform init
terraform plan
terraform apply  # Enter: yes (takes ~5–7 min)
```

### 6. Deploy ML service to RunPod

```bash
cd ../../runpod_service
export HF_TOKEN=your_token
docker build --build-arg PRELOAD_MODELS=true --build-arg HF_TOKEN=$HF_TOKEN -t callsum-ml:latest .
docker tag callsum-ml:latest <your-username>/callsum-ml:latest
docker push <your-username>/callsum-ml:latest
```

Create endpoint on [RunPod Console](https://runpod.io/console/serverless) → New Endpoint → RTX 3090 → set env `HF_TOKEN`.

Update `terraform.tfvars` with `runpod_api_key` and `runpod_endpoint_url`, then `terraform apply`.

### 7. Set Telegram webhook

```bash
WEBHOOK_URL=$(terraform output -raw api_gateway_url)
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$WEBHOOK_URL\"}"
```

### 8. Test it!

Send a voice message to your bot → get a summary back (~2–3 min).

---

## 📚 Detailed Guides

- **[docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** — Full step-by-step deployment
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System design with diagrams
- **[docs/DIGITALOCEAN_SPACES_GUIDE.md](docs/DIGITALOCEAN_SPACES_GUIDE.md)** — DO Spaces alternative
- **[README.md](README.md)** — Project overview

---

## ✅ Checklist

- [ ] All accounts created
- [ ] All tokens obtained and saved
- [ ] Tools installed (Terraform, Docker, AWS CLI)
- [ ] `terraform.tfvars` configured
- [ ] AWS infrastructure deployed (`terraform apply`)
- [ ] Docker image built and pushed
- [ ] RunPod Endpoint created and configured
- [ ] Terraform updated with RunPod credentials
- [ ] Telegram webhook set
- [ ] Bot tested and working
