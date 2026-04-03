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

RUN SECRET_KEY=collectstatic-build-key \
    DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput --clear

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 120 --log-level info labai.wsgi:application"]