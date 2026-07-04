#!/usr/bin/env bash
# One-shot deployment helper.
#   ./deploy.sh local    -> docker compose up
#   ./deploy.sh render   -> push blueprint (requires render CLI + git remote)
#   ./deploy.sh vercel   -> deploy frontend (requires vercel CLI)
set -euo pipefail
cd "$(dirname "$0")/.."

case "${1:-local}" in
  local)
    docker compose -f docker/docker-compose.yml up --build
    ;;
  render)
    command -v render >/dev/null || { echo "Install render CLI first"; exit 1; }
    render blueprint launch deployment/render.yaml
    ;;
  vercel)
    command -v vercel >/dev/null || { echo "npm i -g vercel first"; exit 1; }
    cp deployment/vercel.json frontend/vercel.json
    (cd frontend && vercel --prod)
    ;;
  *)
    echo "usage: deploy.sh [local|render|vercel]"; exit 1 ;;
esac
