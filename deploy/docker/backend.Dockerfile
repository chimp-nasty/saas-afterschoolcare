# The API image (Cloud Run). Built with backend/ as the context:
#
#   docker build -f deploy/docker/backend.Dockerfile backend
#
# Only what backend.Dockerfile.dockerignore lets in reaches the build:
# the app and its requirements. Settings and secrets come from Cloud Run's
# environment (Secret Manager), never from a file in the image.

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Run as a user that can't change the app's files.
RUN useradd --system --no-create-home api
USER api

# Cloud Run sets PORT (8080). Only the load balancer reaches the service,
# so its forwarded headers (scheme, client address) are trusted.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
