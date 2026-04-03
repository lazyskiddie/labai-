#!/bin/bash
set -e

echo "========================================"
echo "LabAI Container Starting"
echo "========================================"
echo "DATABASE_URL: ${DATABASE_URL:0:40}..."
echo "SECRET_KEY set: ${SECRET_KEY:+YES}"
echo "ALLOWED_HOSTS: $ALLOWED_HOSTS"
echo "PORT: ${PORT:-8000}"
echo "========================================"

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput
echo "Migrations complete."

# Start gunicorn
echo "Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers 2 \
  --threads 4 \
  --timeout 120 \
  --log-level info \
  --access-logfile - \
  --error-logfile - \
  labai.wsgi:application