FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps required by WeasyPrint and image/font rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir gunicorn==21.2.0

# Copy project files
COPY . /app

# Create runtime dirs (mount as volumes in production if desired)
RUN mkdir -p /app/generated_pdfs /app/stored_files

# Default runtime environment
ENV PORT=8000 \
    HOST=0.0.0.0 \
    FLASK_ENV=production

EXPOSE 8000

# Start the app with Gunicorn
CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:8000", "server_fixed:app"]


