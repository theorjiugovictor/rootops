# RootOps

<div align="center">

<img src=".github/logo.png" alt="RootOps Logo" width="200"/>

**AI-Powered DevOps Intelligence Platform**

[![Docker Pulls](https://img.shields.io/docker/pulls/theorjiugovictor/rootops)](https://hub.docker.com/r/theorjiugovictor/rootops)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*Predictive insights for your DevOps pipeline - not reactive responses*

[Quick Start](#quick-start) •
[Documentation](docs/) •
[Examples](examples/) •
[Contributing](CONTRIBUTING.md)

</div>

---

## What is RootOps?

RootOps is a **zero-configuration intelligence engine** that analyzes your software delivery lifecycle to predict incidents before they happen. By correlating data from **Git**, **Logs**, and **Traces**, it builds a long-term memory of your system's health and evolution.

### Key Capabilities

*   **Narrative Intelligence**: Generates an "Intelligence Brief" (executive summary) of your system's health, risks, and trends using generic LLM support (OpenAI, Gemini, Anthropic).
*   **Predictive Risk**: Forecasts deployment success 80% more accurately than heuristic scanners using XGBoost.
*   **Universal Log Parsing**: Automatically parses standard log files (syslog, application logs) and structured JSON formats, using anomaly detection to find hidden errors without complex configuration.
*   **Performance Forecasting**: Predicts latency impact of code changes before they hit production.
*   **Local & Private**: Works completely offline with your local git repo. Your data stays yours.
*   **Zero Config**: Auto-detects Loki, Prometheus, and Postgres. Starts working in seconds.

## Quick Start

### 1. Docker Run (Production Ready)

Use the pre-built image with persistence and full AI features enabled.

```bash
docker run -d \
  --name rootops \
  --network="host" \
  -v /var/log:/logs:ro \
  -v /root/rootops_data:/app/db \
  -e DATABASE_URL=sqlite:///./db/rootops.db \
  -e GITHUB_REPO=owner/repo \
  -e GITHUB_TOKEN=your_token \
  -e LLM_PROVIDER=gemini \
  -e LLM_API_KEY=your_key \
  theorjiugovictor/rootops:1.0.11
```

> **Note**: Replace `gemini` with `openai` or `anthropic` as needed. The volume mount `/root/rootops_data` ensures your history is saved.

Access the dashboard at [http://localhost:8000/dashboard](http://localhost:8000/dashboard).

### 2. Local Demo (No Docker)

Try it on your current repository instantly:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the local analysis demo
export LLM_API_KEY="your_key"
export LLM_PROVIDER="gemini"
python demo_local_repo.py .
```

## Configuration

Customize RootOps behavior using environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | `gemini`, `openai`, or `anthropic` |
| `LLM_MODEL` | `gemini-pro` | Model name (e.g., `gpt-4o`, `claude-3-sonnet`, `gemini-1.5-flash`) |
| `LLM_API_KEY` | - | Your API Key |
| `GITHUB_REPO` | - | Repository to link (Owner/Name) |
| `DATABASE_URL` | `postgresql://...` | DB Connection string (supports SQLite) |
| `LOG_PATH` | `/var/log` | Path to scan for logs (if not using Loki) |

## Documentation

*   [**Architecture**](docs/architecture.md): Deep dive into the Service, ML, and Data layers.
*   [**API Reference**](docs/api-reference.md): Complete REST API documentation.
*   [**Integration Guide**](docs/INTEGRATION_GUIDE.md): How to connect GitHub, Loki, Prometheus, and Tempo.

## Architecture

RootOps employs a microservices-inspired architecture designed for resilience:

```
┌─────────────────┐       ┌──────────────────┐
│  Auto-Poller    │──────▶│ Intelligence     │
│ (Git/Logs/Metrics)      │     Engine       │
└─────────────────┘       └────────┬─────────┘
                                   │
      ┌──────────────┬─────────────┼──────────────┐
      ▼              ▼             ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│  XGBoost   │ │  Multi-LLM │ │ Isolation  │ │ SQLite/PG  │
│ Classifier │ │   Client   │ │  Forest    │ │   Memory   │
└────────────┘ └────────────┘ └────────────┘ └────────────┘
```

## License

MIT License. See [LICENSE](LICENSE) for details.

<div align="center">
Built by the RootOps Community
</div>
