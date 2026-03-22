# Handoff Checklist

Дата актуализации: 22 марта 2026

Этот чеклист предназначен для финальной передачи проекта заказчику.

## 1. Финальная подготовка репозитория

- Убедиться, что в рабочем дереве нет временных файлов, локальных секретов и build-артефактов.
- Зафиксировать commit/tag, который передается заказчику.
- Проверить, что заказчику передается именно этот commit/tag, а не “последнее локальное состояние”.

## 2. Локальные проверки перед деплоем

- Выполнить `python3 -m unittest test_llm test_stt test_deployment_contracts`.
- Выполнить `./deployment/build_lambda_package.sh`.
- При необходимости локального бота проверить `.env` и запуск `docker compose up` или `python3 telegram_bot/bot_local.py`.

## 3. Инфраструктура AWS

- Перейти в `infrastructure/terraform`.
- Проверить `terraform.tfvars` или `runpod.auto.tfvars`.
- Выполнить `terraform init`.
- Выполнить `terraform plan`.
- Выполнить `terraform apply`.
- Сохранить outputs после применения.

## 4. RunPod

- Запустить `./deployment/deploy_runpod.sh`.
- Убедиться, что endpoint отвечает на `{"input":{"test":true}}`.
- Проверить, что в RunPod environment variables заданы:
  - `HF_TOKEN`
- Проверить, что в Lambda environment variables заданы:
  - `RUNPOD_ENDPOINT_URL`
  - `RUNPOD_API_KEY_SECRET_ARN` или `RUNPOD_API_KEY`
  - `RUNPOD_CALLBACK_TOKEN`

## 5. Telegram webhook

- Установить webhook через Telegram Bot API.
- Передать тот же `secret_token`, что используется в `TELEGRAM_SECRET_TOKEN`.
- Проверить `getWebhookInfo` и убедиться, что нет `last_error_message`.

## 6. Smoke test end-to-end

- Отправить `/start`.
- Отправить короткое голосовое сообщение 15-60 секунд.
- Убедиться, что задача получает `job_id`.
- Убедиться, что прогресс обновляется или `/status <job_id>` показывает движение.
- Убедиться, что приходит итоговое summary и `transcript.txt`.
- Проверить, что результат записан в storage по пути `users/<user_id>/results/<job_id>.json`.

## 7. Операционная проверка

- Проверить CloudWatch logs Lambda.
- Проверить RunPod logs для worker-а.
- Проверить DynamoDB записи jobs и rate-limits.
- Проверить `GET /health`.
- Проверить, что API Gateway не пишет body trace в CloudWatch.

## 8. Что передать заказчику

- Ссылку на репозиторий или архив с конкретным commit/tag.
- Инструкцию, какие документы читать в первую очередь:
  - `README.md`
  - `docs/HANDOFF_CHECKLIST.md`
  - `docs/PROJECT_STATUS.md`
  - `docs/DEPLOYMENT_GUIDE.md`
- Шаблон конфигурации:
  - `infrastructure/terraform/terraform.tfvars.example`
  - `.env.example`
- Список секретов, которые должны быть заведены отдельно и не хранятся в git.
- Краткий список облачных ресурсов:
  - AWS Lambda
  - API Gateway
  - DynamoDB
  - S3 или DigitalOcean Spaces
  - RunPod endpoint
  - Secrets Manager

## 9. Что не передавать в git

- Реальные `terraform.tfvars`
- Реальные `.env`
- API keys / bot tokens / callback tokens
- `runpod.auto.tfvars`, если он содержит боевые ключи

## 10. Критерий завершения handoff

- Заказчик может развернуть проект по документации без устных пояснений.
- Есть один проверенный deploy path.
- Есть один проверенный smoke test.
- Все секреты вынесены из репозитория.
- Передан конкретный commit/tag и список внешних ресурсов.
