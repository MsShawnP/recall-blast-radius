FROM python:3.13-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Copy API source and pipeline (dockerignore excludes heavy scripts)
COPY api/ api/
COPY pipeline/ pipeline/

# Non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
