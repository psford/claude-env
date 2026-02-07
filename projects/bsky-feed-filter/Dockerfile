FROM python:3.12-slim AS base

# Security: non-root user
RUN groupadd -r feedgen && useradd -r -g feedgen -d /app -s /sbin/nologin feedgen

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY *.py ./

# Create data directory owned by feedgen user
RUN mkdir -p /data && chown feedgen:feedgen /data

USER feedgen

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3000/.well-known/did.json')" || exit 1

EXPOSE 3000

CMD ["python", "server.py"]
