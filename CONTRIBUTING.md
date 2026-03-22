# Contributing to Callsum

Thank you for your interest in contributing to Callsum!

## Getting Started

### Prerequisites

- Python 3.10+
- Docker (for ML service)
- Terraform ≥ 1.0 (for infrastructure)
- AWS CLI 2.x

### Local Setup

```bash
# Clone the repository
git clone https://github.com/sapirl7/Callsum.git
cd Callsum

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your development tokens
```

### Running the Bot Locally

```bash
python3 telegram_bot/bot_local.py
```

This runs the bot in polling mode (no AWS required for basic testing).

### Running Tests

```bash
# Contract tests (no cloud access needed)
python3 -m pytest test_deployment_contracts.py -v

# All tests
python3 -m pytest -v
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `fix/webhook-validation`
- `feat/audio-format-support`
- `docs/update-deployment-guide`

### Code Style

- Follow PEP 8
- Use meaningful variable names
- Add docstrings to public functions
- Keep functions focused and reasonably sized

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add support for mp3 audio format
fix: correct webhook token validation
docs: update deployment guide
chore: update dependencies
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Run tests locally
4. Push and open a PR
5. Fill out the PR template
6. Wait for CI checks to pass
7. Request review

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows existing style
- [ ] Documentation updated (if applicable)
- [ ] No secrets or credentials in code
- [ ] Commit messages follow conventions

## What to Contribute

- 🐛 Bug fixes
- 📖 Documentation improvements
- 🧪 Test coverage
- 🌍 Translations
- ⚡ Performance improvements

## Questions?

Open a [GitHub Discussion](https://github.com/sapirl7/Callsum/discussions) or file an issue.
