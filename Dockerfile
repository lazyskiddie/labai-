FROM python:3.11-slim

# Install Tesseract OCR + system deps
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

# Collect static files at build time — needs dummy credentials
RUN SECRET_KEY=build-only \
    DATABASE_URL=sqlite:////tmp/b.db \
    python manage.py collectstatic --noinput --clear

# Make startup script executable
RUN chmod +x start.sh

EXPOSE 8000

# Use the startup script — easier to debug than inline sh -c
CMD ["/bin/bash", "start.sh"]