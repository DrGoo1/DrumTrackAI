# Use Python 3.11 to ensure prebuilt wheels for pydantic-core/psycopg
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . /app

# Expose default port (Render injects PORT)
ENV PORT=8000
EXPOSE 8000

# Start with gunicorn + uvicorn worker
CMD gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.calibration_api:app --bind 0.0.0.0:$PORT
