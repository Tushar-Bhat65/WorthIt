# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install system packages required to build python packages, Chromium, and Node
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
     build-essential \
     ca-certificates \
     curl \
     wget \
     gnupg \
     unzip \
     fonts-liberation \
     libnss3 \
     libatk1.0-0 \
     libatk-bridge2.0-0 \
     libx11-xcb1 \
     libxcomposite1 \
     libxdamage1 \
     libxrandr2 \
     libgbm1 \
     libasound2 \
     libxss1 \
     libgtk-3-0 \
     libxrender1 \
     libglib2.0-0 \
     libxml2-dev \
     libxslt1-dev \
     libssl-dev \
     libffi-dev \
  && rm -rf /var/lib/apt/lists/*

# Install Google Chrome Stable (so Selenium can use it)
RUN curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-linux-signing-keyring.gpg \
  && echo "deb [signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
    > /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends google-chrome-stable \
  && rm -rf /var/lib/apt/lists/*

# Install Node (for building React / Vite)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
  && apt-get update && apt-get install -y nodejs \
  && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Upgrade pip and install python deps
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install Playwright browsers (chromium only to save space)
RUN python -m playwright install chromium

# Build React frontend (adjust folder name if your frontend folder is named differently)
WORKDIR /app/frontend
RUN npm ci
RUN npm run build

# Move frontend build to static dir served by FastAPI
WORKDIR /app
RUN mkdir -p /app/static
# If your Vite output folder is 'dist' or 'build', change accordingly.
RUN cp -r /app/frontend/dist/* /app/static/ || true
RUN cp -r /app/frontend/build/* /app/static/ || true

# Ensure chrome is discoverable (webdriver-manager will query the chrome version)
ENV CHROME_BIN=/usr/bin/google-chrome-stable

# Expose the port (Render will provide $PORT)
EXPOSE 10000

# Use the $PORT env variable that Render injects at runtime
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]
