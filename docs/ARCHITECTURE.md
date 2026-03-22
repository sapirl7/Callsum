# Architecture

## System Overview

Callsum is a serverless audio analysis pipeline that processes voice recordings through three ML stages and delivers structured meeting notes via Telegram.

```mermaid
graph LR
    subgraph Entry["Entry Point"]
        TG["📱 Telegram Bot"]
    end

    subgraph Orchestration["AWS Orchestration Layer"]
        APIGW["API Gateway"]
        LAMBDA["Lambda<br/>(bot.py)"]
        SM["Secrets Manager"]
    end

    subgraph Storage["Persistence Layer"]
        S3["S3<br/>AES-256"]
        DB["DynamoDB<br/>On-Demand"]
    end

    subgraph ML["ML Processing Layer — RunPod"]
        W["🎙 Whisper large-v3<br/>Transcription"]
        P["👥 Pyannote 3.1<br/>Speaker Diarization"]
        L["🤖 Llama 3.1 8B<br/>Summarization (vLLM)"]
    end

    subgraph Monitoring["Observability"]
        CW["CloudWatch"]
        SNS["SNS Alerts"]
        BUD["Budget Alarms"]
    end

    TG --> APIGW --> LAMBDA
    LAMBDA --> SM
    LAMBDA --> S3
    LAMBDA --> DB
    LAMBDA -.->|trigger| W
    W --> P --> L
    L -.->|callback| LAMBDA
    LAMBDA --> CW
    CW --> SNS
    LAMBDA --> BUD
```

---

## Component Responsibilities

| Component | File | Runtime | Responsibility |
|-----------|------|---------|---------------|
| **Telegram Bot** | `telegram_bot/bot.py` | AWS Lambda | Accept audio, validate, upload to S3, create job, trigger RunPod, deliver results |
| **ML Worker** | `runpod_service/handler.py` | RunPod Serverless GPU | Download audio, transcribe, diarize, summarize, upload result, send callback |
| **Infrastructure** | `infrastructure/terraform/*.tf` | Terraform | Provision all AWS resources as code |
| **Deployment Scripts** | `deployment/*.sh` | Shell | Automate build & deploy steps |

---

## Security Model

```mermaid
flowchart TB
    subgraph Secrets["🔐 Never in code or env"]
        BOT_TOKEN["Telegram Bot Token"]
        RUNPOD_KEY["RunPod API Key"]
        DO_KEYS["DO Spaces Keys<br/>(optional)"]
    end

    subgraph AWS_SM["AWS Secrets Manager"]
        SM_BOT["token (bot)"]
        SM_RP["api_key (runpod)"]
        SM_DO["access/secret (spaces)"]
    end

    subgraph Data["🛡 Data at rest"]
        S3_ENC["S3 — AES-256 SSE"]
        S3_VER["S3 — Versioning ON"]
        DB_PITR["DynamoDB — PITR"]
    end

    subgraph Transport["🔒 Data in transit"]
        PRESIGNED["Presigned URLs<br/>(1hr expiry)"]
        TLS["TLS everywhere"]
        SECRET_HDR["Webhook secret tokens"]
    end

    BOT_TOKEN --> SM_BOT
    RUNPOD_KEY --> SM_RP
    DO_KEYS --> SM_DO

    SM_BOT --> LAMBDA["Lambda reads at init"]
    SM_RP --> LAMBDA

    LAMBDA -->|generates| PRESIGNED
    PRESIGNED -->|used by| GPU["RunPod Worker"]
```

**Key decisions:**
- RunPod **never** gets AWS credentials — only time-limited presigned URLs
- Telegram webhook is validated via `X-Telegram-Bot-Api-Secret-Token`
- RunPod callback is validated via `X-Runpod-Callback-Token`
- All S3 data is encrypted at rest (AES-256 SSE)
- DynamoDB records auto-expire via TTL (30 days)
- S3 audio files auto-delete via lifecycle rules (30 days)

---

## ML Pipeline Detail

```mermaid
flowchart LR
    A["📥 Download Audio<br/>(presigned URL)"] --> B["🎙 Whisper large-v3<br/>word-level timestamps"]
    B --> C["👥 Pyannote 3.1<br/>speaker segments"]
    C --> D["🔗 Align<br/>words ↔ speakers"]
    D --> E["📝 Format<br/>timestamped dialogue"]
    E --> F["🤖 Llama 3.1 8B<br/>JSON summary via vLLM"]
    F --> G["📤 Upload Result<br/>(presigned URL)"]
    G --> H["📲 Callback<br/>→ Lambda → Telegram"]

    style F fill:#ffa,stroke:#aa0
```

**Graceful degradation**: If the LLM (step 6) fails, the pipeline still returns the full speaker-labeled transcript. The `llm_error` field is populated in the result metadata so the bot can inform the user.

---

## Processing Time Estimates

| Audio Length | Transcription | Diarization | Summary | Total |
|-------------|---------------|-------------|---------|-------|
| 5 min | ~30s | ~20s | ~10s | **~1 min** |
| 30 min | ~3 min | ~2 min | ~30s | **~6 min** |
| 1 hour | ~6 min | ~4 min | ~1 min | **~11 min** |
| 2 hours | ~12 min | ~8 min | ~2 min | **~22 min** |

*Estimates on RTX 3090. Actual times depend on GPU availability and cold start.*

---

## Storage Layout

```
s3://callsum-prod/
├── users/{user_id}/
│   ├── audio/new/{job_id}.ogg    # Uploaded audio (30-day retention)
│   └── results/{job_id}.json     # Processing result (90-day retention)
```

DynamoDB tables:
- `callsum-jobs` — job tracking (job_id, status, progress, timestamps)
- `callsum-jobs-rate-limits` — per-user rate counters with TTL
