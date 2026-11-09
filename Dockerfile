# VitalFrame — self-hosted personal health-data framework
FROM python:3.11-slim

WORKDIR /app

# Install build + runtime deps
COPY pyproject.toml ./
COPY vitalframe ./vitalframe
COPY README.md ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Data volume holds the SQLite store + rendered dashboard
VOLUME ["/app/data"]
EXPOSE 8899

# Default: serve the dashboard with periodic rebuild.
# Override CMD to run one-shot builds: vitalframe build --config config.yaml --output data/vitalframe_dashboard.html
CMD ["sh", "-c", "vitalframe ingest --config config.yaml || true && vitalframe serve --config config.yaml --host 0.0.0.0 --port 8899"]
