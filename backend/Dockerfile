# ====================================================================
# DermaSense AI - Backend Container (FastAPI, ONNX, PyTorch, FAISS)
# Smart India Hackathon 2025 (Team Healthnautix, PS 25049)
# ====================================================================
FROM python:3.11-slim

WORKDIR /app

# System dependencies for PyTorch / FAISS / Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend service and clinical knowledge bases
COPY backend /app/backend
COPY data /app/data
COPY ml/weights /app/ml/weights

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

