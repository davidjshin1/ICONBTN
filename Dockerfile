# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend + Serve Frontend
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies for PIL, fonts, and Playwright
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libfontconfig1 \
    fonts-dejavu-core \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright dependencies (for gacha generation)
RUN pip install playwright && playwright install chromium --with-deps

# Copy and install Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY assets/ ./assets/
COPY fonts/ ./fonts/

# Copy frontend build to static directory
COPY --from=frontend-build /app/frontend/dist ./static/

# Create output directories
RUN mkdir -p output/icon output/cta output/card output/boon output/gacha

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Start the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
