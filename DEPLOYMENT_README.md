# 🚀 Callsum — Deployment Guide (Summary)

> **Status:** Supplementary overview guide.
> **Canonical handoff documents:** `docs/HANDOFF_CHECKLIST.md`, `docs/PROJECT_STATUS.md`, `docs/DEPLOYMENT_GUIDE.md`.

**Secure, Scalable Call Transcription & Summarization System**

## ✨ Features

- 🎯 **Transcription** — Whisper large-v3 (Russian language)
- 👥 **Diarization** — speaker identification (Pyannote 3.1)
- 📋 **Structured summary** — Llama 3.1 8B Instruct
  - Commerce, Operations, Technical sections
  - Action items with owners and deadlines
- 📱 **Telegram integration** — just send a voice message
- 🔒 **Full security** — encryption, isolation, least privilege
- 💰 **Cost-effective** — ~$10–15/month at 60 hours of audio

---

## 🎯 Quick Start

```bash
git clone https://github.com/sapirl7/Callsum.git
cd Callsum/infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your tokens

terraform init && terraform apply

# Deploy RunPod ML service
cd ../../deployment && ./deploy_runpod.sh

# Set Telegram webhook
WEBHOOK_URL=$(cd ../infrastructure/terraform && terraform output -raw api_gateway_url)
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"$WEBHOOK_URL\"}"
```

Send a voice message to your bot — done! 🎉

---

## 📖 Full Documentation

See [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) for detailed instructions.

---

## 💰 Cost

| Service | Monthly |
|---------|---------|
| AWS (Lambda, S3, DynamoDB, API GW, Secrets) | ~$2–3 |
| RunPod GPU (RTX 3090, ~20 hrs) | ~$8–11 |
| **Total** | **$10–15** |

---

## 🔒 Security

- ✅ Encryption at rest (S3 AES-256, DynamoDB)
- ✅ Encryption in transit (HTTPS everywhere)
- ✅ User isolation (S3 paths by user_id)
- ✅ Least privilege (IAM)
- ✅ Secrets Manager (tokens & keys)
- ✅ Audit trail (CloudWatch Logs)
- ✅ Auto-deletion (S3 Lifecycle, 30 days)

---

## 🔧 Troubleshooting

```bash
# Check webhook
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Check Lambda logs
aws logs tail /aws/lambda/callsum-telegram-bot-prod --follow
```

See full troubleshooting in [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md#troubleshooting).

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
