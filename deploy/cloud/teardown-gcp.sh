#!/usr/bin/env bash
# ─── RootOps — Teardown Google Cloud Deployment ─────────────────
# Removes the GCE VM and associated firewall rules.
#
# Usage:
#   ./deploy/cloud/teardown-gcp.sh
#   # or:
#   make cloud-teardown

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Load .env
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

: "${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"

ZONE="${GCP_ZONE:-us-central1-a}"
VM_NAME="${VM_NAME:-rootops}"

echo ""
echo -e "${RED}${BOLD}RootOps — Cloud Teardown${NC}"
echo ""
echo "  This will permanently delete:"
echo "    • VM: $VM_NAME (zone: $ZONE)"
echo "    • All data on the VM (database, models, etc.)"
echo "    • Firewall rule: rootops-allow-https"
echo ""
read -p "  Are you sure? Type 'yes' to confirm: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""

# Delete VM
echo -e "${YELLOW}▸${NC} Deleting VM '$VM_NAME'..."
if gcloud compute instances delete "$VM_NAME" \
    --zone="$ZONE" --project="$GCP_PROJECT_ID" --quiet 2>/dev/null; then
    echo -e "${GREEN}✓${NC} VM deleted"
else
    echo -e "${YELLOW}⚠${NC} VM not found (already deleted?)"
fi

# Delete firewall rule
echo -e "${YELLOW}▸${NC} Deleting firewall rule..."
if gcloud compute firewall-rules delete rootops-allow-https \
    --project="$GCP_PROJECT_ID" --quiet 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Firewall rule deleted"
else
    echo -e "${YELLOW}⚠${NC} Firewall rule not found (already deleted?)"
fi

echo ""
echo -e "${GREEN}✓${NC} Teardown complete. All cloud resources removed."
echo ""
echo "  Note: Your Duck DNS subdomain still exists."
echo "  To remove it, visit: https://www.duckdns.org"
echo ""
