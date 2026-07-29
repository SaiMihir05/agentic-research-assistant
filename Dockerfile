# Use official Python slim image for smaller layers
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (postgres client for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them first (leverages Docker cache)
COPY requirements.txt ./
RUN pip install --no-cache-dir --timeout=120 --retries=5 -r requirements.txt

# Copy the whole source code
COPY . .

# Expose the default FastAPI port (8000)
EXPOSE 8000

# Use the environment variable PORT if provided, default to 8000
ENV PORT=8000

# Run the app with uvicorn (autoreload disabled for production)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
