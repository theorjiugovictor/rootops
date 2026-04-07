# Contributing to RootOps

Thank you for your interest in contributing to RootOps! This guide will help you get started.

## Development Setup

### Prerequisites

- Docker & Docker Compose v2+
- Python 3.11+ (for local development without Docker)
- Git

### Quick Start (Docker)

```bash
git clone https://github.com/rootops-dev/rootops-v3.git
cd rootops-v3
cp .env.example .env
make dev          # starts all services with hot-reload
```

### Local Development (without Docker)

```bash
# API
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Web UI (runs in container for supply chain isolation)
make web
```

You'll need a PostgreSQL instance with pgvector and an Ollama instance running locally.

## Project Structure

```
rootops/
├── api/                 # FastAPI backend (RAG engine, LLM dispatch)
│   ├── app/
│   │   ├── api/         # Route handlers
│   │   ├── models/      # SQLAlchemy models
│   │   └── services/    # LLM clients, embeddings, git ingestor
│   └── Dockerfile
├── web/                 # Next.js dashboard (TypeScript, Tailwind)
│   ├── src/             # App Router pages + components
│   └── Dockerfile
├── docker-compose.yml   # Production stack
└── Makefile             # Developer shortcuts
```

## How to Contribute

### Reporting Bugs

- Check existing issues first to avoid duplicates
- Use the bug report template
- Include: steps to reproduce, expected vs actual behaviour, environment details

### Suggesting Features

- Open a feature request issue
- Describe the use case, not just the solution
- Be open to discussion on implementation approach

### Submitting Pull Requests

1. **Fork** the repository and create a branch from `main`
2. **Name your branch** descriptively: `feat/openai-backend`, `fix/embedding-crash`, `docs/api-guide`
3. **Write tests** for new functionality
4. **Follow the code style** (see below)
5. **Keep PRs focused** — one feature or fix per PR
6. **Update documentation** if your change affects the user experience
7. **Write a clear PR description** explaining what and why

### Code Style

- **Python**: Follow PEP 8. Use type hints. Docstrings on public functions.
- **Imports**: Group by stdlib → third-party → local, separated by blank lines
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Async**: Use `async/await` consistently — the API is fully async

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add Anthropic LLM backend
fix: handle empty embedding vectors on ingest
docs: add deployment guide for Railway
refactor: extract LLM dispatch to separate module
```

Prefix with: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

## Adding a New LLM Backend

RootOps is designed to support multiple LLM providers. To add a new one:

1. Create `api/app/services/your_client.py` — implement `async def generate_your_provider(...) -> str`
2. Add config vars to `api/app/config.py` (API key, model name, etc.)
3. Add the dispatch case in `api/app/services/llm_backend.py`
4. Document the new backend in `.env.example`
5. Add the provider to the README backends table

See `openai_client.py` or `anthropic_client.py` as reference implementations.

## Running Tests

```bash
# Run all tests
make test

# Run specific test file
cd api && python -m pytest tests/test_query.py -v
```

## Community

- Be respectful and constructive
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)
- Ask questions in GitHub Discussions

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
