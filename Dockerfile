# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    CHROME_BIN=/usr/bin/chromium

# Install system dependencies for Playwright, Chromium, and Selenium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg ca-certificates wget unzip fonts-liberation \
    libnss3 libatk-bridge2.0-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libasound2 libpangocairo-1.0-0 libcups2 libxss1 libxcursor1 libxext6 \
    libxrender1 libxi6 libxtst6 libatk1.0-0 libatspi2.0-0 libxkbcommon0 chromium \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY requirements.txt /app/requirements.txt
COPY . /app

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Install Playwright + browsers
RUN pip install playwright && \
    playwright install chromium


# Install ChromeDriver for Selenium
RUN CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver && \
    rm /tmp/chromedriver.zip

# Expose FastAPI port
EXPOSE 8000

# Default command to run FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
