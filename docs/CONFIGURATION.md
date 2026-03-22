# Configuration

Ключевые параметры:

## Telegram / Lambda

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_TOKEN_SECRET_ARN`
- `TELEGRAM_SECRET_TOKEN`
- `RUNPOD_CALLBACK_TOKEN`

## RunPod

- `RUNPOD_ENDPOINT_URL`
- `RUNPOD_API_KEY`
- `RUNPOD_API_KEY_SECRET_ARN`
- `HF_TOKEN`

## Storage / DB

- `S3_BUCKET_NAME`
- `S3_ENDPOINT_URL`
- `DO_SPACES_SECRET_ARN`
- `DYNAMODB_TABLE_NAME`
- `RATE_LIMITS_TABLE_NAME`

## Runtime limits

- `MAX_AUDIO_DURATION_SECONDS`
- `MIN_AUDIO_DURATION_SECONDS`
- `MAX_FILE_SIZE_MB`
- `FREE_TIER_REQUESTS_PER_HOUR`
- `FREE_TIER_REQUESTS_PER_DAY`
- `MAX_RETRIES`
- `RETRY_MIN_WAIT_SECONDS`
- `RETRY_MAX_WAIT_SECONDS`

Для локальной разработки можно использовать корневой `.env`, а для AWS deployment основной источник значений находится в Terraform variables и Lambda environment variables.
