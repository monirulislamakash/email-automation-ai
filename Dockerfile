# -----------------------------------------------------------------------------
# Stage 1: install dependencies (compilers + build tools stay here only)
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: runtime — no compilers, only the venv + app code
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Crawl4AI (website_scraper.AsyncWebCrawler) drives headless Chromium via Playwright.
# The slim image has no browser; without this step scraping works locally but fails in Docker.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && playwright install --with-deps chromium

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
