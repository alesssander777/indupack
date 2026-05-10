#!/usr/bin/env bash
# Render (e outros PaaS) definem PORT; localmente usa 10000.
PORT="${PORT:-10000}"
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"