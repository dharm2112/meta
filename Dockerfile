# ── Stage 1: build React frontend ────────────────────────────────────
FROM node:20-slim AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --legacy-peer-deps
COPY frontend/ ./
RUN npm run build
# produces /build/dist/

# ── Stage 2: production image ────────────────────────────────────────
FROM python:3.11-slim

RUN useradd -m -u 1000 appuser
WORKDIR /app/backend

# Python deps (cached layer)
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend source
COPY backend/ ./

# Ensure local packages are importable
ENV PYTHONPATH=/app/backend

# Built frontend → backend/static (FastAPI serves it)
COPY --from=frontend-build /build/dist ./static

# Pre-train RL checkpoint so the demo works out of the box
RUN python train_rl.py --episodes 1000

EXPOSE 7860
ENV PORT=7860

USER appuser
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
