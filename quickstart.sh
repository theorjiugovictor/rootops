#!/bin/bash

# RootOps Quick Start Script
# This script helps you get RootOps running in under 1 minute

set -e

echo "============================================"
echo "  RootOps - Quick Start"
echo "============================================"
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✓ Docker is installed"
echo ""

# Get GitHub token
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Enter your GitHub Personal Access Token:"
    echo "(Get one from: https://github.com/settings/tokens)"
    echo "Required scopes: repo (read-only)"
    echo ""
    read -sp "GitHub Token: " GITHUB_TOKEN
    echo ""
fi

# Get GitHub repo
if [ -z "$GITHUB_REPO" ]; then
    echo ""
    echo "Enter your GitHub repository (format: owner/repo):"
    echo "Example: microsoft/vscode"
    echo ""
    read -p "Repository: " GITHUB_REPO
fi

echo ""
echo "Configuration:"
echo "  Repository: $GITHUB_REPO"
echo "  Token: ${GITHUB_TOKEN:0:10}..."
echo ""

# Optional: Observability backends
read -p "Do you have Grafana Loki? (y/n) [n]: " has_loki
if [ "$has_loki" = "y" ] || [ "$has_loki" = "Y" ]; then
    read -p "Loki URL [http://loki:3100]: " LOKI_URL
    LOKI_URL=${LOKI_URL:-http://loki:3100}
    LOKI_ARG="-e LOKI_URL=$LOKI_URL"
fi

read -p "Do you have Prometheus? (y/n) [n]: " has_prom
if [ "$has_prom" = "y" ] || [ "$has_prom" = "Y" ]; then
    read -p "Prometheus URL [http://prometheus:9090]: " PROMETHEUS_URL
    PROMETHEUS_URL=${PROMETHEUS_URL:-http://prometheus:9090}
    PROM_ARG="-e PROMETHEUS_URL=$PROMETHEUS_URL"
fi

echo ""
echo "Starting RootOps..."
echo ""

# Run RootOps
docker run -d \
  --name rootops \
  -p 8000:8000 \
  -e GITHUB_TOKEN="$GITHUB_TOKEN" \
  -e GITHUB_REPO="$GITHUB_REPO" \
  $LOKI_ARG \
  $PROM_ARG \
  rootops/rootops

echo ""
echo "============================================"
echo "  RootOps is now running!"
echo "============================================"
echo ""
echo "Dashboard: http://localhost:8000/dashboard"
echo "API Docs:  http://localhost:8000/docs"
echo "Health:    http://localhost:8000/health"
echo ""
echo "What's happening now:"
echo "  1. Auto-polling GitHub for new commits every 5 minutes"
echo "  2. Analyzing commit risk automatically"
echo "  3. Monitoring logs (if Loki configured)"
echo "  4. Learning patterns continuously"
echo ""
echo "View logs: docker logs -f rootops"
echo "Stop:      docker stop rootops"
echo "Remove:    docker rm rootops"
echo ""
echo "Open dashboard in:"
sleep 2
if command -v open &> /dev/null; then
    open http://localhost:8000/dashboard
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8000/dashboard
else
    echo "http://localhost:8000/dashboard"
fi
