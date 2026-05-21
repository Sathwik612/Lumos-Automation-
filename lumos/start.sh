#!/bin/bash
cd "$(dirname "$0")/backend"

# Load .env if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

uvicorn main:app --reload --host 0.0.0.0 --port 8000
