# Minimal fast build - skip apt-get, use wget for healthcheck
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements-prod.txt .

# Install Python packages with binary wheels only (FAST - no compilation)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --only-binary :all: -r requirements-prod.txt || \
    pip install --no-cache-dir --prefer-binary -r requirements-prod.txt

# Copy application code
COPY src ./src
COPY .env* ./

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser && chown -R appuser:appuser /app

USER appuser

ENV PYTHONPATH=/app PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Use Python for healthcheck (no curl needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
