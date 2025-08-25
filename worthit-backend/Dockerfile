# Playwright image with browsers & deps preinstalled (simplest for scraping)
FROM mcr.microsoft.com/playwright/python:latest

# Faster pip & no bytecode files
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Workdir
WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of your app
COPY . .

# Expose FastAPI port
EXPOSE 8000

# IMPORTANT: single process (no gunicorn) so your shared Playwright browser stays alive
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "8000"]
