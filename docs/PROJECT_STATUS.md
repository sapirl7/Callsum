# Project Status

Дата актуализации: 22 марта 2026

## Текущее состояние

Проект находится в состоянии `deployment candidate`.
Критические блокеры из аудита закрыты в коде и IaC, но production readiness всё ещё зависит от одного внешнего staging/E2E прогона с реальными облачными ресурсами.

## Что исправлено

- RunPod worker теперь запускается как настоящий serverless worker.
- Telegram bot больше не зависит от import-time AWS side effects.
- RunPod callback теперь аутентифицируется отдельным token-ом.
- Lambda теперь пакуется вместе с Python зависимостями.
- Terraform outputs исправлены для сценария с `count` и DO Spaces.
- Корневые Docker/dev-файлы больше не ссылаются на удалённый `pipeline.py` и старый Ollama flow.
- Псевдо-тесты заменены на реальные smoke-contract tests.

## Что проверено локально

- Синтаксис Python через `py_compile`.
- Smoke-contract tests через `python3 -m unittest test_llm test_stt test_deployment_contracts`.
- Актуальность ключевых handoff и deployment docs.

## Что не проверено в этом репозитории автоматически

- Реальный `terraform apply`.
- Build/push Docker image в registry.
- Реальное создание RunPod endpoint.
- Telegram webhook с боевым bot token.
- Полный e2e цикл от голосового сообщения до итогового summary в Telegram.

## Остаточные риски

- Любые реальные сетевые/облачные проблемы будут видны только на staging.
- Стоимость и производительность RunPod зависят от выбранного GPU и cold start профиля.
- Локальный режим без AWS всё ещё ограничен: для полной обработки нужен доступ к storage/DynamoDB/RunPod.

## Канонические документы

- `README.md`
- `docs/README.md`
- `docs/HANDOFF_CHECKLIST.md`
- `docs/DEPLOYMENT_GUIDE.md`

## Документы вспомогательного характера

- `QUICK_START.md`
- `DEPLOYMENT_GUIDE_FULL.md`
- `DEPLOYMENT_README.md`
- `README_DEPLOYMENT.md`
- `presentation.html`
