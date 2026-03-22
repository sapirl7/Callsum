# 🎙️ Callsum — AI Call Summarizer

> Turn any voice recording into structured meeting notes with speaker diarization in minutes.

![Status](https://img.shields.io/badge/Status-Deployment_Candidate-orange)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

## What It Does

Send a voice message or audio file to a Telegram bot → get back:

- 📋 **Structured Summary** — key points split into Commerce / Operations / Technical
- 📌 **Action Items** — tasks with assigned owners, deadlines, and priorities
- 📄 **Full Transcript** — speaker-labeled, timestamped transcript as a `.txt` file

**Cost per hour of audio: ~$0.15** (GPU compute only, zero cost when idle).

---

## Architecture

```
┌─────────────┐
│  📱 Telegram │
└──────┬──────┘
       │ voice / audio
       ▼
┌──────────────────────────────────────┐
│            ☁️  AWS Cloud              │
│                                      │
│  API Gateway → Lambda (bot.py)       │
│                  │                   │
│        ┌────────┼────────┐           │
│        ▼        ▼        ▼           │
│       S3    DynamoDB  Secrets Mgr    │
│   (AES-256)  (jobs)   (tokens)      │
└────────┬─────────────────────────────┘
         │ presigned URL
         ▼
┌──────────────────────────────────────┐
│         🚀  RunPod Serverless GPU     │
│                                      │
│  1. Whisper large-v3  (transcribe)   │
│  2. Pyannote 3.1      (diarize)     │
│  3. Llama 3.1 8B      (summarize)   │
└──────────────────────────────────────┘
         │ callback
         ▼
    📱 Results → Telegram
```

---

## ML Pipeline

| Stage | Model | What It Does |
|-------|-------|-------------|
| 1. Transcription | **Whisper large-v3** | Speech → text with word timestamps |
| 2. Diarization | **Pyannote 3.1** | Identify who said what |
| 3. Summarization | **Llama 3.1 8B Instruct** | Structured JSON summary via vLLM |

**Minimum GPU**: RTX 3090 (24 GB) or A4000 (16 GB)

**Graceful degradation**: if the LLM fails, the bot still returns the full transcript with speaker labels.

---

## Project Structure

```
callsum/
├── telegram_bot/
│   ├── bot.py                # Lambda handler — webhook + callback
│   ├── bot_local.py          # Local dev — polling mode
│   └── requirements.txt
│
├── runpod_service/
│   ├── handler.py            # GPU worker — Whisper + Pyannote + Llama
│   ├── Dockerfile            # CUDA 12.1 + model preloading
│   └── requirements.txt
│
├── infrastructure/
│   └── terraform/            # Complete IaC
│       ├── main.tf, lambda.tf, api_gateway.tf
│       ├── s3.tf, dynamodb.tf, iam.tf
│       ├── secrets.tf, monitoring.tf
│       └── variables.tf
│
├── deployment/
│   ├── deploy_aws.sh         # One-click AWS deployment
│   ├── deploy_runpod.sh      # One-click RunPod deployment
│   └── build_lambda_package.sh
│
└── docs/                     # 📖 Documentation
    ├── ARCHITECTURE.md        # System design & diagrams
    ├── CONFIGURATION.md       # All environment variables
    ├── API.md                 # Webhook & callback contracts
    ├── HANDOFF_CHECKLIST.md   # Deployment checklist
    ├── PROJECT_STATUS.md      # Current status
    └── PUBLISH_READINESS_REPORT.md
```

---

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| AWS CLI | 2.x | Cloud management |
| Terraform | ≥ 1.0 | Infrastructure provisioning |
| Docker | Latest | RunPod image build |
| Python | 3.10+ | Local development |

### 1. Clone & configure

```bash
git clone https://github.com/sapirl7/Callsum.git
cd Callsum/infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your tokens
```

### 2. Deploy infrastructure

```bash
terraform init && terraform plan && terraform apply
```

### 3. Deploy ML service

```bash
cd ../../deployment
./deploy_runpod.sh
```

### 4. Set Telegram webhook

```bash
WEBHOOK_URL=$(cd ../infrastructure/terraform && terraform output -raw api_gateway_url)
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${WEBHOOK_URL}\"}"
```

### 5. Test it

Send a voice message to your bot → get a summary back!

---

## Cost Breakdown (100 calls/month)

| Service | Cost |
|---------|------|
| AWS Lambda | $0.20 |
| S3 (encrypted) | $0.50 |
| DynamoDB (on-demand) | $0.25 |
| API Gateway | $0.35 |
| Secrets Manager | $1.20 |
| **RunPod GPU** (30 hrs × $0.44) | **$13.20** |
| **Total** | **~$16/month** |

> **Zero idle cost** — serverless architecture means $0 when nobody is using it.

---

## Supported Formats

`.ogg` · `.mp3` · `.wav` · `.m4a` · `.webm`

**Limits**: max 2 hours, max 100 MB, 10 req/hr per user.

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, security model |
| [CONFIGURATION.md](docs/CONFIGURATION.md) | All environment variables with defaults |
| [API.md](docs/API.md) | Webhook and callback API contracts |
| [HANDOFF_CHECKLIST.md](docs/HANDOFF_CHECKLIST.md) | Step-by-step deployment checklist |
| [PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | What works, what needs staging |
| [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Detailed deployment walkthrough |

---

## License

MIT — see [LICENSE](LICENSE) for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) — speech recognition
- [Pyannote Audio](https://github.com/pyannote/pyannote-audio) — speaker diarization
- [Meta Llama 3.1](https://ai.meta.com/llama/) — text summarization
- [RunPod](https://runpod.io) — serverless GPU infrastructure
- [vLLM](https://github.com/vllm-project/vllm) — high-throughput LLM serving
