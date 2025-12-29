#!/bin/bash
# Docker Release Script for RootOps

set -e

echo "============================================"
echo "  RootOps Docker Release"
echo "============================================"
echo ""

# Check if version provided
if [ -z "$1" ]; then
    echo "Usage: ./release.sh v1.0.0"
    echo ""
    echo "This will:"
    echo "  1. Create a git tag"
    echo "  2. Push to GitHub"
    echo "  3. Trigger Docker build via GitHub Actions"
    echo ""
    exit 1
fi

VERSION=$1

# Validate version format
if [[ ! $VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format v1.0.0"
    exit 1
fi

echo "Preparing release: $VERSION"
echo ""

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "Warning: You have uncommitted changes"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag already exists
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "Error: Tag $VERSION already exists"
    exit 1
fi

echo "Creating tag: $VERSION"
git tag -a "$VERSION" -m "Release $VERSION"

echo "Pushing tag to GitHub..."
git push origin "$VERSION"

echo ""
echo "============================================"
echo "  Release $VERSION Initiated"
echo "============================================"
echo ""
echo "GitHub Actions is now building your Docker image."
echo ""
echo "Monitor progress:"
echo "  https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:\/]\(.*\)\.git/\1/')/actions"
echo ""
echo "Once complete, your image will be available as:"
echo "  docker pull youruser/rootops:$VERSION"
echo "  docker pull youruser/rootops:latest"
echo ""
