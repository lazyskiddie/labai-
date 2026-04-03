FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p staticfiles static

# Collect static at build time using dummy credentials (no DB needed)
RUN SECRET_KEY=collectstatic-build-key \
    DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput --clear

EXPOSE 8000

# Startup: print env info for debugging, then migrate, then gunicorn
CMD ["sh", "-c", "\
    echo '=== LabAI Starting ===' && \
    echo 'DATABASE_URL set:' ${DATABASE_URL:+YES} ${DATABASE_URL:-NO_NOT_SET} && \
    echo 'SECRET_KEY set:' ${SECRET_KEY:+YES} ${SECRET_KEY:-NO_NOT_SET} && \
    python manage.py migrate --noinput 2>&1 && \
    echo '=== Migrations done, starting gunicorn ===' && \
    exec gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 120 --log-level info labai.wsgi:application \
"]