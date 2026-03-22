<![CDATA[# 🎙️ Callsum — AI Call Summarizer

> Turn any voice recording into structured meeting notes with speaker diarization in minutes.

![Status](https://img.shields.io/badge/Status-Deployment_Candidate-orange)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

<p align="center">
  <img src="https://img.shields.io/badge/Whisper-large--v3-blueviolet" alt="whisper"/>
  <img src="https://img.shields.io/badge/Pyannote-3.1-ff69b4" alt="pyannote"/>
  <img src="https://img.shields.io/badge/Llama-3.1--8B--Instruct-orange" alt="llama"/>
  <img src="https://img.shields.io/badge/Infra-Terraform-623CE4" alt="terraform"/>
</p>

---

## What It Does

Send a voice message or audio file to a Telegram bot → get back:

| Output | Description |
|--------|-------------|
| 📋 **Structured Summary** | Key points split into Commerce / Operations / Technical |
| 📌 **Action Items** | Tasks with assigned owners, deadlines, and priorities |
| 📄 **Full Transcript** | Speaker-labeled, timestamped transcript as a `.txt` file |

**Cost per hour of audio: ~$0.15** (GPU compute only, zero cost when idle).

---

## Architecture

```mermaid
flowchart TB
    subgraph User
        TG["📱 Telegram"]
    end

    subgraph AWS["☁️ AWS Cloud"]
        APIGW["API Gateway<br/><i>webhook endpoint</i>"]
        LAMBDA["Lambda<br/><i>bot.py</i>"]
        S3["S3 Bucket<br/><i>AES-256 encrypted</i>"]
        DYNAMO["DynamoDB<br/><i>jobs + rate limits</i>"]
        SM["Secrets Manager<br/><i>tokens & keys</i>"]
        CW["CloudWatch<br/><i>logs, metrics, alarms</i>"]
    end

    subgraph RunPod["🚀 RunPod Serverless"]
        GPU["GPU Worker<br/><i>handler.py</i>"]
        WHISPER["Whisper large-v3<br/><i>transcription</i>"]
        PYANNOTE["Pyannote 3.1<br/><i>speaker diarization</i>"]
        LLAMA["Llama 3.1 8B<br/><i>summarization</i>"]
    end

    TG -- "voice / audio" --> APIGW
    APIGW --> LAMBDA
    LAMBDA -- "upload audio" --> S3
    LAMBDA -- "create job" --> DYNAMO
    LAMBDA -- "read secrets" --> SM
    LAMBDA -- "trigger (presigned URL)" --> GPU
    GPU --> WHISPER --> PYANNOTE --> LLAMA
    GPU -- "upload result" --> S3
    GPU -- "callback" --> LAMBDA
    LAMBDA -- "send result" --> TG
    LAMBDA -.-> CW
```

---

## Data Flow

```mermaid
sequenceDiagram
    actor U as User
    participant T as Telegram
    participant L as Lambda (bot.py)
    participant S3 as S3
    participant DB as DynamoDB
    participant R as RunPod GPU

    U->>T: Send voice/audio
    T->>L: Webhook POST
    L->>L: Rate limit check
    L->>S3: Upload audio (AES-256)
    L->>DB: Create job record
    L->>R: POST /run (presigned URLs)
    L->>T: "✅ Processing started!"
    
    R->>S3: Download audio (presigned)
    R->>R: Whisper → Pyannote → Llama
    R->>S3: Upload result JSON (presigned)
    R->>L: Callback (COMPLETED)
    
    L->>DB: Update job → completed
    L->>T: Send summary + transcript.txt
    T->>U: 📋 Results delivered
```

---

## Project Structure

```
callsum/
├── telegram_bot/
│   ├── bot.py              # Lambda handler — Telegram webhook + RunPod callback
│   ├── bot_local.py         # Local dev — polling mode (no AWS required for testing)
│   └── requirements.txt
│
├── runpod_service/
│   ├── handler.py           # GPU worker — Whisper + Pyannote + Llama 3.1
│   ├── Dockerfile           # CUDA 12.1 + model preloading
│   └── requirements.txt
│
├── infrastructure/
│   └── terraform/           # Complete IaC — Lambda, API GW, S3, DynamoDB, etc.
│       ├── main.tf
│       ├── lambda.tf
│       ├── api_gateway.tf
│       ├── s3.tf
│       ├── dynamodb.tf
│       ├── iam.tf
│       ├── secrets.tf
│       ├── monitoring.tf
│       └── variables.tf
│
├── deployment/
│   ├── deploy_aws.sh        # One-click AWS deployment
│   ├── deploy_runpod.sh     # One-click RunPod deployment
│   ├── build_lambda_package.sh
│   └── validate_deployment.sh
│
├── docs/                    # 📖 All documentation lives here
│   ├── README.md            # Documentation index
│   ├── ARCHITECTURE.md      # System design & data flow
│   ├── CONFIGURATION.md     # All environment variables
│   ├── API.md               # Webhook & callback contracts
│   ├── HANDOFF_CHECKLIST.md # Step-by-step deployment checklist
│   └── PROJECT_STATUS.md    # Current status & known limitations
│
└── test_deployment_contracts.py  # Contract smoke tests
```

---

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| AWS CLI | 2.x | Cloud management |
| Terraform | ≥ 1.0 | Infrastructure provisioning |
| Docker | Latest | RunPod image build |
| Python | 3.10+ | Local development & tests |

### 1. Clone & configure

```bash
git clone https://github.com/sapirl7/Callsum.git
cd Callsum

# Terraform variables
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your tokens and keys
```

### 2. Deploy infrastructure

```bash
terraform init
terraform plan
terraform apply
```

### 3. Deploy ML service

```bash
cd ../../deployment
./deploy_runpod.sh
```

### 4. Set Telegram webhook

```bash
WEBHOOK_URL=$(cd ../infrastructure/terraform && terraform output -raw api_gateway_url)
BOT_TOKEN="your-bot-token"

curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${WEBHOOK_URL}\"}"
```

### 5. Test it

Send a voice message to your bot → get a summary back!

---

## ML Pipeline

| Stage | Model | What It Does | Resource |
|-------|-------|-------------|----------|
| 1. Transcription | **Whisper large-v3** | Speech → text with word timestamps | ~3 GB VRAM |
| 2. Diarization | **Pyannote 3.1** | Identify who said what | ~1 GB VRAM |
| 3. Summarization | **Llama 3.1 8B Instruct** | Structured JSON summary via vLLM | ~10 GB VRAM |

**Minimum GPU**: RTX 3090 (24 GB) or A4000 (16 GB)

**Graceful degradation**: if the LLM fails, the bot still returns the full transcript with speaker labels.

---

## Cost Breakdown

### Monthly estimate (100 calls/month)

| Service | Cost |
|---------|------|
| AWS Lambda | $0.20 |
| S3 (encrypted, versioned) | $0.50 |
| DynamoDB (on-demand) | $0.25 |
| API Gateway | $0.35 |
| CloudWatch | $0.30 |
| Secrets Manager | $1.20 |
| **RunPod GPU** (30 hrs × $0.44) | **$13.20** |
| **Total** | **~$16/month** |

> **Zero idle cost** — serverless architecture means $0 when nobody is using it.

---

## Supported Formats

| Format | Source |
|--------|--------|
| `.ogg` | Telegram voice messages |
| `.mp3` | Standard audio files |
| `.wav` | Uncompressed audio |
| `.m4a` | Apple / mobile recordings |
| `.webm` | Browser recordings |

**Limits**: max 2 hours duration, max 100 MB file size, 10 req/hr and 50 req/day per user.

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow diagrams, security model |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | All environment variables with defaults |
| [docs/API.md](docs/API.md) | Webhook and callback API contracts |
| [docs/HANDOFF_CHECKLIST.md](docs/HANDOFF_CHECKLIST.md) | Step-by-step deployment & verification checklist |
| [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) | What works, what needs staging verification |
| [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Detailed deployment walkthrough |

---

## License

MIT — see [LICENSE](LICENSE) for details.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) — speech recognition
- [Pyannote Audio](https://github.com/pyannote/pyannote-audio) — speaker diarization
- [Meta Llama 3.1](https://ai.meta.com/llama/) — text summarization
- [RunPod](https://runpod.io) — serverless GPU infrastructure
- [vLLM](https://github.com/vllm-project/vllm) — high-throughput LLM serving
]]>
