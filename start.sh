#!/bin/bash
set -e
mkdir -p static/logs
uvicorn main:app --host 0.0.0.0 --port $PORT
