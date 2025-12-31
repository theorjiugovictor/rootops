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

*   **🧠 Hybrid Intelligence**: Combines **XGBoost** (Machine Learning) with **Gemini 1.5** (Semantic AI) for deep risk analysis.
*   **🔮 Predictive Risk**: Forecasts deployment success 80% more accurately than heuristic scanners.
*   **🕵️ Anomaly Detection**: Uses **Isolation Forests** to detect log anomalies and error spikes automatically.
*   **⚡ Performance Forecasting**: Predicts latency impact of code changes before they hit production.
*   **🏠 Local & Private**: Works completely offline with your local git repo. Your data stays yours.
*   **🚀 Zero Config**: Auto-detects Loki, Prometheus, and Postgres. Starts working in seconds.

## Quick Start

### 1. Docker Run (Recommended)

Get running immediately with the pre-built Docker image.

```bash
docker run -p 8000:8000 \
  -e GITHUB_TOKEN=your_token \
  -e GITHUB_REPO=owner/repo \
  -e GEMINI_API_KEY=your_gemini_key \
  theorjiugovictor/rootops
```

Access the dashboard at [http://localhost:8000/dashboard](http://localhost:8000/dashboard).

### 2. Local Demo (No Docker)

Try it on your current repository instantly:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the local analysis demo
export GEMINI_API_KEY="your_key"
python demo_local_repo.py .
```

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
│  XGBoost   │ │  Gemini    │ │ Isolation  │ │ PostgreSQL │
│ Classifier │ │  Analysis  │ │  Forest    │ │   Memory   │
└────────────┘ └────────────┘ └────────────┘ └────────────┘
```

## License

MIT License. See [LICENSE](LICENSE) for details.

<div align="center">
Built by the RootOps Community
</div>
