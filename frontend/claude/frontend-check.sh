#!/usr/bin/env bash
set -euo pipefail

# frontend-check.sh — tsc + vite + vitest in Docker
IMAGE=node:20-bookworm
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== TypeScript type-check ==="
docker run --rm -v "$ROOT:/app" -w /app $IMAGE \
  sh -c "npm ci --ignore-scripts 2>/dev/null; npx tsc --noEmit"

echo ""
echo "=== Vite build ==="
docker run --rm -v "$ROOT:/app" -w /app $IMAGE \
  sh -c "npm ci --ignore-scripts 2>/dev/null; npx vite build"

echo ""
echo "=== Vitest ==="
docker run --rm -v "$ROOT:/app" -w /app $IMAGE \
  sh -c "npm ci --ignore-scripts 2>/dev/null; npx vitest run --reporter=dot"
