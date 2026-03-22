# Handoff Checklist

Last updated: March 22, 2026

This checklist is intended for the final project handoff to the client.

## 1. Repository Preparation

- Ensure no temporary files, local secrets, or build artifacts remain in the working tree.
- Tag the commit being delivered to the client.
- Verify the client receives this exact commit/tag, not just "the latest local state".

## 2. Local Pre-Deploy Checks

- Run `python3 -m unittest test_llm test_stt test_deployment_contracts`.
- Run `./deployment/build_lambda_package.sh`.
- If testing the bot locally, check `.env` and run `docker compose up` or `python3 telegram_bot/bot_local.py`.

## 3. AWS Infrastructure

- Navigate to `infrastructure/terraform`.
- Verify `terraform.tfvars` (or `runpod.auto.tfvars`).
- Run `terraform init`.
- Run `terraform plan`.
- Run `terraform apply`.
- Save outputs after applying.

## 4. RunPod

- Run `./deployment/deploy_runpod.sh`.
- Confirm the endpoint responds to `{"input": {"test": true}}`.
- Verify RunPod environment variables:
  - `HF_TOKEN`
- Verify Lambda environment variables:
  - `RUNPOD_ENDPOINT_URL`
  - `RUNPOD_API_KEY_SECRET_ARN` or `RUNPOD_API_KEY`
  - `RUNPOD_CALLBACK_TOKEN`

## 5. Telegram Webhook

- Set the webhook via the Telegram Bot API.
- Pass the same `secret_token` used in `TELEGRAM_SECRET_TOKEN`.
- Check `getWebhookInfo` and ensure there is no `last_error_message`.

## 6. End-to-End Smoke Test

- Send `/start`.
- Send a short voice message (15–60 seconds).
- Confirm the job receives a `job_id`.
- Confirm progress updates appear (or `/status <job_id>` shows progression).
- Confirm the final summary and `transcript.txt` are delivered.
- Verify the result is stored at `users/<user_id>/results/<job_id>.json`.

## 7. Operational Verification

- Check CloudWatch logs for Lambda.
- Check RunPod logs for the worker.
- Check DynamoDB records (jobs and rate-limits).
- Test `GET /health`.
- Verify API Gateway does not log body traces to CloudWatch.

## 8. What to Deliver

- Link to the repository or archive with the specific commit/tag.
- Instructions on which documents to read first:
  - `README.md`
  - `docs/HANDOFF_CHECKLIST.md`
  - `docs/PROJECT_STATUS.md`
  - `docs/DEPLOYMENT_GUIDE.md`
- Configuration templates:
  - `infrastructure/terraform/terraform.tfvars.example`
  - `.env.example`
- List of secrets that must be provisioned separately (not stored in git).
- Summary of cloud resources:
  - AWS Lambda
  - API Gateway
  - DynamoDB
  - S3 or DigitalOcean Spaces
  - RunPod endpoint
  - Secrets Manager

## 9. What NOT to Commit

- Real `terraform.tfvars`
- Real `.env`
- API keys / bot tokens / callback tokens
- `runpod.auto.tfvars` if it contains production keys

## 10. Handoff Completion Criteria

- The client can deploy the project using the documentation alone, without verbal explanations.
- There is one verified deploy path.
- There is one verified smoke test.
- All secrets are removed from the repository.
- A specific commit/tag and list of external resources have been delivered.
