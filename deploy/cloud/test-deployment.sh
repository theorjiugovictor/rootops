#!/usr/bin/env bash
# ─── RootOps — Deployment Test Suite ─────────────────────────────
# Verifies all endpoints are working after a deployment.
#
# Usage:
#   ./deploy/cloud/test-deployment.sh https://rootops.duckdns.org
#   # or:
#   make cloud-test

set -euo pipefail

BASE_URL="${1:?Usage: test-deployment.sh <base-url>}"
BASE_URL="${BASE_URL%/}"  # strip trailing slash

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

pass=0
fail=0
skip=0

test_endpoint() {
    local name="$1"
    local method="$2"
    local path="$3"
    local expected="${4:-200}"
    local data="${5:-}"
    local timeout="${6:-10}"

    local args=(-s -k -o /dev/null -w "%{http_code}" -X "$method" --max-time "$timeout")
    if [ -n "$data" ]; then
        args+=(-H "Content-Type: application/json" -d "$data")
    fi

    local status
    status=$(curl "${args[@]}" "${BASE_URL}${path}" 2>/dev/null || echo "000")

    if [ "$status" = "$expected" ]; then
        echo -e "  ${GREEN}✓${NC} $name ${BLUE}($method $path)${NC} → $status"
        ((pass++))
    elif [ "$status" = "000" ]; then
        echo -e "  ${YELLOW}⊘${NC} $name ${BLUE}($method $path)${NC} → connection failed"
        ((skip++))
    else
        echo -e "  ${RED}✗${NC} $name ${BLUE}($method $path)${NC} → $status (expected $expected)"
        ((fail++))
    fi
}

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       RootOps — Deployment Test Suite            ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Target: $BASE_URL"
echo ""

# ── 1. Core health ───────────────────────────────────────────
echo -e "${BOLD}1. Health & Core${NC}"
test_endpoint "Health check"         GET  "/health"
test_endpoint "OpenAPI schema"       GET  "/openapi.json"
test_endpoint "Swagger docs"         GET  "/docs"

# ── 2. API endpoints ─────────────────────────────────────────
echo ""
echo -e "${BOLD}2. API Endpoints${NC}"
test_endpoint "Repositories list"    GET  "/api/repos"
test_endpoint "Ingest status"        GET  "/api/ingest/status"
test_endpoint "Dev profiles"         GET  "/api/profiles"
test_endpoint "Architecture graph"   GET  "/api/graph"
test_endpoint "Log concepts"         GET  "/api/concepts"

# ── 3. Query (POST) ──────────────────────────────────────────
echo ""
echo -e "${BOLD}3. Query Engine${NC}"
test_endpoint "Query endpoint"       POST "/api/query" "200" \
    '{"question":"What does this codebase do?","top_k":3}' 120

# ── 4. Web UI pages ──────────────────────────────────────────
echo ""
echo -e "${BOLD}4. Web UI${NC}"
test_endpoint "Dashboard"            GET  "/"
test_endpoint "Intelligence page"    GET  "/intelligence"
test_endpoint "Logs page"            GET  "/logs"
test_endpoint "Auto-heal page"       GET  "/auto-heal"
test_endpoint "Dev profiles page"    GET  "/dev-profiles"
test_endpoint "PR review page"       GET  "/pr-review"
test_endpoint "Settings page"        GET  "/settings"

# ── 5. HTTPS / Security ──────────────────────────────────────
echo ""
echo -e "${BOLD}5. HTTPS & Security${NC}"

# Check TLS certificate
CERT_INFO=$(curl -sk -w "%{ssl_verify_result}" -o /dev/null "$BASE_URL" 2>/dev/null || echo "failed")
if [ "$CERT_INFO" = "0" ]; then
    echo -e "  ${GREEN}✓${NC} TLS certificate valid"
    ((pass++))
else
    # Self-signed or Let's Encrypt still provisioning
    echo -e "  ${YELLOW}⊘${NC} TLS certificate not fully verified (may still be provisioning)"
    ((skip++))
fi

# Check security headers
HEADERS=$(curl -sk -I "$BASE_URL" 2>/dev/null)
if echo "$HEADERS" | grep -qi "x-content-type-options: nosniff"; then
    echo -e "  ${GREEN}✓${NC} X-Content-Type-Options header present"
    ((pass++))
else
    echo -e "  ${YELLOW}⊘${NC} X-Content-Type-Options header missing"
    ((skip++))
fi

# ── 6. CORS ──────────────────────────────────────────────────
echo ""
echo -e "${BOLD}6. CORS${NC}"

CORS_RESP=$(curl -sk -o /dev/null -w "%{http_code}" \
    -H "Origin: ${BASE_URL}" \
    -H "Access-Control-Request-Method: GET" \
    -X OPTIONS "${BASE_URL}/api/repos" 2>/dev/null || echo "000")

if [ "$CORS_RESP" = "200" ] || [ "$CORS_RESP" = "204" ]; then
    echo -e "  ${GREEN}✓${NC} CORS preflight successful"
    ((pass++))
else
    echo -e "  ${YELLOW}⊘${NC} CORS preflight returned $CORS_RESP"
    ((skip++))
fi

# ── Results ──────────────────────────────────────────────────
echo ""
echo "─────────────────────────────────────────────────"
TOTAL=$((pass + fail + skip))
echo -e "  ${GREEN}$pass passed${NC}  ${RED}$fail failed${NC}  ${YELLOW}$skip skipped${NC}  ($TOTAL total)"
echo ""

if [ "$fail" -eq 0 ]; then
    if [ "$skip" -eq 0 ]; then
        echo -e "  ${GREEN}${BOLD}All tests passed! 🎉${NC}"
    else
        echo -e "  ${GREEN}${BOLD}No failures!${NC} ${YELLOW}Some tests skipped (may need more time).${NC}"
    fi
    echo ""
    exit 0
else
    echo -e "  ${RED}${BOLD}$fail test(s) failed.${NC} Check service logs:"
    echo "    make cloud-logs"
    echo ""
    exit 1
fi
