# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- MIT License
- Security policy (SECURITY.md)
- Contributing guide (CONTRIBUTING.md)
- CI pipeline (GitHub Actions: lint, test, terraform validate, security scan)
- Dependabot for automated dependency updates
- Issue and PR templates
- EditorConfig
- `.dockerignore` for RunPod service
- Non-root user in Dockerfile

### Changed
- All documentation and comments translated to English
- Mermaid diagrams in README replaced with ASCII art for reliable rendering
- Docker container now runs as non-root user

## [2.0.0] - 2026-03-22

### Added
- AWS Lambda + API Gateway for Telegram bot
- RunPod Serverless integration for ML processing
- Terraform IaC for complete infrastructure provisioning
- Whisper large-v3 transcription
- Pyannote 3.1 speaker diarization
- Llama 3.1 8B Instruct structured summarization via vLLM
- S3 encrypted storage with 30-day lifecycle
- DynamoDB job tracking and rate limiting
- Secrets Manager integration
- CloudWatch monitoring and budget alarms
- DigitalOcean Spaces as alternative to S3
- Comprehensive deployment documentation

### Changed
- Llama 3 70B → Llama 3.1 8B Instruct (60% GPU cost savings)
- vLLM 0.3.0 → 0.6.3
- Removed SQS (direct RunPod call with callback)
- Webhook token validation added

### Fixed
- Lambda packaging with dependencies
- Telegram bot import-time AWS side effects
- RunPod callback authentication
- Terraform output for count-based resources

## [1.0.0] - 2026-01-15

### Added
- Initial MVP: local audio processing
- Whisper + Pyannote + Ollama pipeline
- Basic Telegram bot with polling mode
- Simple text summary output
