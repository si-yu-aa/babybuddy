# Baby Buddy with Social Feed
# Based on Python 3.12 Alpine

FROM python:3.12-alpine

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=babybuddy.settings.base

# Install system dependencies
RUN apk add --no-cache \
    build-base \
    jpeg-dev \
    zlib-dev \
    libffi-dev \
    openssl-dev \
    cairo \
    gdk-pixbuf \
    pango \
    musl \
    cargo \
    rust

# Install Python dependencies
WORKDIR /app

# Copy dependency files
COPY requirements.txt Pipfile Pipfile.lock ./

# Install Python packages
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt channels channels-redis daphne

# Copy project
COPY . .

# Remove all translation files (using hardcoded Chinese instead)
RUN rm -rf /app/locale/*

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run with daphne (ASGI server with WebSocket support)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "babybuddy.asgi:application"]
