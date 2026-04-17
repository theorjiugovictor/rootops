#!/usr/bin/env python3
"""
RootOps demo seeder — run via `make demo`.

Seeds the running API with:
  1. Synthetic log entries for three fictional services.
  2. Optionally ingests a small public GitHub repo so the UI has code to query.

Usage (inside Docker):
    docker compose exec api python api/scripts/seed_demo.py

Usage (local):
    python api/scripts/seed_demo.py [--api-url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import urllib.error

# ── Config ────────────────────────────────────────────────────────

DEFAULT_API = "http://localhost:8000"

DEMO_LOGS: list[dict] = [
    {
        "service_name": "payment-service",
        "source": "raw",
        "raw_text": """\
2025-11-14 09:31:02,456 ERROR payment_processor: InsufficientFundsError: balance 0 < amount 5000 for account acc_9912
  File "app/services/payment_processor.py", line 87, in process_payment
    raise InsufficientFundsError(...)
2025-11-14 09:31:45,123 ERROR ledger: LedgerError: currency mismatch GBP != USD for transfer txn_4421
2025-11-14 09:32:01,000 WARN  fraud_detector: High-risk score 0.91 for account acc_0033
2025-11-14 09:33:12,301 INFO  payment_processor: Payment txn_5512 completed in 142ms
2025-11-14 09:34:00,000 ERROR payment_processor: Timeout waiting for bank ACK after 30s — txn_5513
""",
    },
    {
        "service_name": "auth-service",
        "source": "raw",
        "raw_text": """\
2025-11-15 08:00:01,000 WARN  auth: Failed login attempt for user@example.com from 192.168.1.42 (attempt 3/5)
2025-11-15 08:00:15,200 ERROR auth: JWT signing key rotation failed — KeyVaultError: secret not found
2025-11-15 08:01:00,000 INFO  auth: User user@example.com authenticated via SSO in 84ms
2025-11-15 08:05:30,100 ERROR auth: Token refresh rejected — refresh_token expired for session sess_8812
2025-11-15 08:06:00,000 WARN  auth: Rate limit triggered for IP 10.0.0.99 (60 req/min exceeded)
""",
    },
    {
        "service_name": "notification-service",
        "source": "raw",
        "raw_text": """\
2025-11-16 12:00:01,000 INFO  notifier: Email queued for user_2281 — order confirmation #ORD-9921
2025-11-16 12:00:05,400 WARN  smtp: SMTP connection pool exhausted (pool_size=10) — queuing retry
2025-11-16 12:00:10,100 ERROR notifier: SendGrid API error 429 — rate limit exceeded, backing off 60s
2025-11-16 12:01:12,000 INFO  notifier: Batch of 50 push notifications delivered in 320ms
2025-11-16 12:02:00,000 ERROR notifier: Dead-letter queue overflow — 512 messages dropped
""",
    },
]

# Small public repo — fast to clone, few commits, good for demo
DEMO_REPO = {
    "repo_url": "https://github.com/pallets/click.git",
    "branch":   "main",
    "max_commits": 20,
    "name":     "click",
    "team":     "demo",
    "tags":     ["demo", "python", "cli"],
    "description": "Pallets/click — seeded automatically by make demo",
}


# ── Helpers ───────────────────────────────────────────────────────

def post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        return {"ok": False, "error": f"HTTP {exc.code}: {body[:200]}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def wait_for_api(base: str, retries: int = 15) -> bool:
    for i in range(retries):
        try:
            with urllib.request.urlopen(f"{base}/health", timeout=3):
                return True
        except Exception:  # noqa: BLE001
            if i < retries - 1:
                print(f"  Waiting for API… ({i + 1}/{retries})")
                time.sleep(2)
    return False


# ── Main ──────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed RootOps with demo data.")
    parser.add_argument("--api-url", default=DEFAULT_API, help="Base URL of the RootOps API")
    parser.add_argument("--skip-repo", action="store_true", help="Skip repo ingestion (logs only)")
    args = parser.parse_args()

    base = args.api_url.rstrip("/")

    print(f"Connecting to RootOps API at {base} …")
    if not wait_for_api(base):
        print("ERROR: API did not respond. Is `make up` running?", file=sys.stderr)
        sys.exit(1)

    # 1. Seed logs
    print("\nSeeding demo logs …")
    for entry in DEMO_LOGS:
        res = post(f"{base}/api/ingest/logs", entry)
        if res.get("ok"):
            n = res.get("entries_ingested", "?")
            print(f"  ✓ {entry['service_name']} — {n} entries ingested")
        else:
            print(f"  ✗ {entry['service_name']} — {res.get('error', 'unknown error')}")

    # 2. Ingest demo repo (optional — takes a minute)
    if not args.skip_repo:
        print(f"\nIngesting demo repo ({DEMO_REPO['repo_url']}) …")
        print("  This may take 30–90 s depending on network speed.")
        res = post(f"{base}/api/ingest", DEMO_REPO)
        if res.get("ok"):
            print(f"  ✓ {DEMO_REPO['name']} ingested — {res.get('message', 'done')}")
        else:
            err = res.get("error", "unknown error")
            print(f"  ✗ Repo ingest failed: {err}")
            print("    Re-run with --skip-repo to seed only logs.")

    print("\nDone! Open http://localhost:3000 to explore the demo data.")
    print("  Try asking: 'How is error handling implemented?'")
    print("  Or visit the Logs page to see the seeded entries.")


if __name__ == "__main__":
    main()
