#!/usr/bin/env bash
# One-shot deployment helper.
#   ./deploy.sh local     -> docker compose up (backend + frontend, local dev)
#   ./deploy.sh backend   -> deploy backend to Vercel (requires vercel CLI, linked project)
#   ./deploy.sh frontend  -> deploy frontend to Vercel (requires vercel CLI, linked project)
#
# Both backend and frontend deploy as SEPARATE Vercel projects from this one
# repo — see docs/DEPLOYMENT.md for first-time setup (Root Directory, env vars).
set -euo pipefail
cd "$(dirname "$0")/.."

case "${1:-local}" in
  local)
    docker compose -f docker/docker-compose.yml up --build
    ;;
  backend)
    command -v vercel >/dev/null || { echo "npm i -g vercel first"; exit 1; }
    (cd backend && vercel --prod)
    ;;
  frontend)
    command -v vercel >/dev/null || { echo "npm i -g vercel first"; exit 1; }
    cp deployment/vercel.json frontend/vercel.json
    (cd frontend && vercel --prod)
    ;;
  *)
    echo "usage: deploy.sh [local|backend|frontend]"; exit 1 ;;
esac
