#!/bin/bash
# Deploy manual de emergencia — ejecutar directamente en el VPS
set -e

REPO_DIR="/opt/etl-bd/proyectos-rrhh/lavanderia/app-lavanderia"

echo "[deploy] $(date) — Iniciando deploy manual..."
cd "$REPO_DIR"

GIT_SSH_COMMAND="ssh -i ~/.ssh/id_bgacitua" git pull origin main

docker compose pull backend frontend
docker compose up -d --no-deps --wait backend
docker compose up -d --no-deps --wait frontend
docker image prune -f

echo "[deploy] $(date) — Deploy completado."
