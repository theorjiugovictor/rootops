# GitHub Integration Guide

RootOps can enrich commit analysis with detailed data from GitHub's API, providing powerful ML-driven insights about code changes and their potential impact.

## Overview

When configured with GitHub access, RootOps automatically fetches:
- Detailed file change statistics
- Lines added/deleted per file
- Author information and commit history
- Code churn metrics
- Directory structure impact (blast radius)

This data feeds into ML models that predict:
- Breaking change probability
- Deployment risk scores
- Performance degradation likelihood
- Author-specific risk patterns

## Setup

### 1. Create GitHub Personal Access Token

1. Go to [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Give it a descriptive name: "RootOps Analysis Token"
4. Select scopes:
   - `repo` (only if private repos) OR
   - `public_repo` (for public repos only)
   - `read:user` (optional, for user metadata)
5. Click "Generate token"
6. Copy the token (starts with `ghp_`)

### 2. Configure RootOps

Add to your `.env` file or environment variables:

```bash
GITHUB_TOKEN=ghp_your_token_here
GITHUB_REPO=owner/repository  # e.g., "facebook/react"
```

### 3. Docker Compose Setup

```yaml
services:
  rootops:
    environment:
      - GITHUB_TOKEN=ghp_your_token_here
      - GITHUB_REPO=owner/repository
```

### 4. Kubernetes Setup

Create a secret:

```bash
kubectl create secret generic rootops-github \
  --from-literal=token=ghp_your_token_here \
  --from-literal=repo=owner/repository
```

Update deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
      - name: rootops
        env:
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: rootops-github
              key: token
        - name: GITHUB_REPO
          valueFrom:
            secretKeyRef:
              name: rootops-github
              key: repo
```

## How It Works

### Without GitHub Integration

Basic analysis using commit hash only:

```json
{
  "commit_hash": "abc123",
  "changed_files": 5,
  "lines_added": 120,
  "lines_deleted": 30,
  "risky_patterns": ["db_migration"],
  "complexity_delta": 0.25
}
```

### With GitHub Integration

Enhanced analysis with rich data:

```json
{
  "commit_hash": "abc123",
  "changed_files": 12,
  "lines_added": 456,
  "lines_deleted": 78,
  "risky_patterns": ["db_migration", "auth_logic", "api_contract"],
  "risk_score": 7.8,
  "blast_radius": 4,
  "test_ratio": 0.33,
  "commit_type": "feature",
  "author": "Jane Developer",
  "author_commits_90d": 47,
  "author_avg_files": 3.2,
  "complexity_delta": 0.68
}
```

## ML Features Extracted

### Risk Score (0-10)
Calculated from:
- Number of files changed
- Total lines of code modified (churn)
- Test coverage ratio
- Commit time (weekends/nights = higher risk)

### Blast Radius
Number of distinct directories/modules affected by the commit.

### Test Ratio
Percentage of changed files that are tests:
- 0.0 = No test coverage
- 1.0 = All changes are tests

### Commit Type Classification
Automatically categorized as:
- `bugfix` - Fix, patch, hotfix
- `feature` - New functionality
- `refactor` - Code improvements
- `test` - Test additions
- `documentation` - Docs only
- `other` - Uncategorized

### Author Risk Profile
Based on 90-day history:
- Total commits in period
- Average files changed per commit
- Recent activity level

## API Rate Limits

GitHub API limits:
- **Authenticated**: 5,000 requests/hour
- **Unauthenticated**: 60 requests/hour

RootOps caches commit data to minimize API calls.

## Security Best Practices

1. **Use read-only tokens** - Only grant `repo:read` scope
2. **Rotate tokens regularly** - Update every 90 days
3. **Use secrets management** - Never commit tokens to git
4. **Scope to specific repos** - Use fine-grained tokens when possible
5. **Monitor token usage** - Check GitHub settings for activity

## Troubleshooting

### "GitHub integration not configured"

Check that both `GITHUB_TOKEN` and `GITHUB_REPO` are set:

```bash
echo $GITHUB_TOKEN
echo $GITHUB_REPO
```

### "GitHub API error: 401 Unauthorized"

Token is invalid or expired. Generate a new token.

### "GitHub API error: 404 Not Found"

- Repository name format is wrong (should be `owner/repo`)
- Token doesn't have access to the repository
- Repository doesn't exist

### "GitHub API error: 403 Rate Limit"

Too many requests. RootOps will fall back to heuristic analysis.

## Fallback Behavior

If GitHub integration fails (network error, rate limit, invalid token), RootOps automatically falls back to heuristic analysis with reduced accuracy.

## Example Usage

### Analyze a Specific Commit

```bash
curl -X POST http://localhost:8000/api/v1/analyze/commit \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "myapp",
    "commit_hash": "a1b2c3d4e5f6"
  }'
```

With GitHub integration enabled, this will:
1. Fetch commit details from GitHub API
2. Extract file changes and statistics
3. Calculate ML risk features
4. Return enriched analysis

### Monitor CI/CD Pipeline

Integrate into your deployment pipeline:

```yaml
# .github/workflows/deploy.yml
steps:
  - name: Analyze commit risk
    run: |
      RISK_SCORE=$(curl -X POST http://rootops:8000/api/v1/analyze/commit \
        -H "Content-Type: application/json" \
        -d "{\"repository\": \"$GITHUB_REPOSITORY\", \"commit_hash\": \"$GITHUB_SHA\"}" \
        | jq '.risk_score')
      
      if (( $(echo "$RISK_SCORE > 8.0" | bc -l) )); then
        echo "High risk commit detected! Consider staged rollout."
        exit 1
      fi
```

## Advanced Configuration

### Multiple Repositories

To analyze multiple repositories, deploy multiple RootOps instances or dynamically pass the repository parameter.

### Custom Risk Thresholds

Adjust in `.env`:

```bash
BREAKING_CHANGE_THRESHOLD=0.7  # 0-1 scale
```

### Webhook Integration (Future)

GitHub webhooks support is planned for real-time analysis on every push.

## Next Steps

- [Integrate with Prometheus](prometheus.md) for metrics
- [Connect to Loki](loki.md) for log correlation
- [Use Tempo](tempo.md) for trace analysis
- [API Reference](../api-reference.md) for all endpoints
