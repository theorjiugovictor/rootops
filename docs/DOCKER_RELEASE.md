# Docker Build and Release Guide

## Prerequisites

1. **Docker Hub Account**
   - Sign up at https://hub.docker.com
   - Create a repository named `rootops`

2. **GitHub Secrets** (one-time setup)
   
   Go to: `https://github.com/yourorg/rootops/settings/secrets/actions`
   
   Add these secrets:
   - `DOCKERHUB_USERNAME`: Your Docker Hub username
   - `DOCKERHUB_TOKEN`: Docker Hub access token (create at https://hub.docker.com/settings/security)

## Release Process

### Automated (Recommended)

```bash
# Make release script executable
chmod +x release.sh

# Create and push a release
./release.sh v1.0.0
```

This will:
1. Create a git tag
2. Push to GitHub
3. Trigger GitHub Actions workflow
4. Build multi-platform Docker image (AMD64 + ARM64)
5. Push to Docker Hub as `rootops:v1.0.0` and `rootops:latest`

Monitor progress at: https://github.com/yourorg/rootops/actions

### Manual Build (Testing)

```bash
# Build locally
docker build -t youruser/rootops:v1.0.0 .

# Test the image
docker run -p 8000:8000 \
  -e GITHUB_TOKEN=your_token \
  -e GITHUB_REPO=owner/repo \
  -e ALLOW_DB_INIT_FAILURE=true \
  youruser/rootops:v1.0.0

# Verify it works
curl http://localhost:8000/health

# Push to Docker Hub
docker login
docker push youruser/rootops:v1.0.0
docker tag youruser/rootops:v1.0.0 youruser/rootops:latest
docker push youruser/rootops:latest
```

## Version Strategy

- **v1.0.0**: First production release
- **v1.1.0**: Minor updates, new features
- **v1.0.1**: Bug fixes, patches
- **latest**: Always points to newest stable release

## Testing Before Release

```bash
# Build locally
docker build -t rootops:test .

# Run with minimal config
docker run -p 8000:8000 -e ALLOW_DB_INIT_FAILURE=true rootops:test

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/
open http://localhost:8000/docs

# Test with GitHub integration
docker run -p 8000:8000 \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  -e GITHUB_REPO=yourorg/yourrepo \
  rootops:test

open http://localhost:8000/dashboard
```

## Troubleshooting

### GitHub Actions Fails

Check workflow logs:
```bash
# View latest workflow run
gh run list --workflow=docker.yml
gh run view <run-id>
```

### Docker Hub Push Denied

Verify secrets:
- `DOCKERHUB_USERNAME` is correct
- `DOCKERHUB_TOKEN` is valid (not expired)
- Repository exists on Docker Hub

### Build Fails Locally

```bash
# Check Python version (must be 3.11 or 3.12)
python --version

# Clear Docker cache
docker builder prune -a

# Build with no cache
docker build --no-cache -t rootops:test .
```

## First Release Checklist

- [ ] Docker Hub account created
- [ ] Repository `rootops` created on Docker Hub
- [ ] GitHub secrets configured (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`)
- [ ] Tested build locally
- [ ] Updated README.md with correct Docker Hub username
- [ ] Run `./release.sh v1.0.0`
- [ ] Verify on Docker Hub
- [ ] Test pull and run: `docker pull youruser/rootops:v1.0.0`

## Post-Release

After successful release:

```bash
# Update README badge
# Change: rootops/rootops -> youruser/rootops

# Test the public image
docker pull youruser/rootops:latest
docker run -p 8000:8000 \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  -e GITHUB_REPO=yourorg/yourrepo \
  youruser/rootops:latest

# Announce on GitHub Releases
gh release create v1.0.0 --title "v1.0.0" --notes "First stable release"
```
