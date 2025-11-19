# Configuration file for Callsum
# All configurable parameters in one place

# Audio processing limits
MAX_AUDIO_DURATION_SECONDS = 7200  # 2 hours
MIN_AUDIO_DURATION_SECONDS = 1
MAX_FILE_SIZE_MB = 100

# Rate limiting (per user)
FREE_TIER_REQUESTS_PER_HOUR = 10
FREE_TIER_REQUESTS_PER_DAY = 50

# ML Models
WHISPER_MODEL = "large-v3"  # Options: tiny, base, small, medium, large-v2, large-v3
PYANNOTE_MODEL = "pyannote/speaker-diarization-3.1"
LLAMA_MODEL = "meta-llama/Meta-Llama-3-70B-Instruct"

# Processing timeouts
RUNPOD_TIMEOUT_SECONDS = 3600  # 1 hour max for GPU processing
LAMBDA_TIMEOUT_SECONDS = 60

# S3 Lifecycle
S3_AUDIO_RETENTION_DAYS = 30
S3_RESULTS_RETENTION_DAYS = 90

# DynamoDB
DYNAMODB_TTL_DAYS = 30

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_MULTIPLIER = 2
RETRY_MIN_WAIT_SECONDS = 2
RETRY_MAX_WAIT_SECONDS = 10

# Telegram message limits
TELEGRAM_MAX_MESSAGE_LENGTH = 4000
