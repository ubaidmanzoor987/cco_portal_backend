#!/bin/bash

# Fail on error.
set -e

# Always flush output
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Log command (for writing to stderr, unlike echo.)
log() { printf "%s\n" "$*" >&2; }

# Set some baseline variables.
PYTHON="${PYTHON:-/usr/bin/env python}"
MANAGE="${MANAGE:-$PYTHON manage.py}"

cd /app/

# Parse commandline.
command=$1
shift

if [ "$command" = "serve" ]; then
  # Migrate database.
  if [ "$RUN_MIGRATE" = "True" ]; then
    log "Running migrations"
    $MANAGE migrate --noinput
  fi

  # Start the Django server.
  log "Starting Django server and Celery worker"
  $MANAGE runserver 0.0.0.0:8000 &
  celery -A conf  worker --loglevel=info
else
  # Handle other commands here.
  exec "$@"
fi
