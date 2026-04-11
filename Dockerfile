# Stage 1: Build frontend
FROM node:20 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Serve backend & frontend
FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY backend/ ./backend/
COPY inference.py ./

# Copy React build to backend's static directory
COPY --from=frontend-builder /app/frontend/dist /app/backend/static

# Set Python path
ENV PYTHONPATH=/app:/app/backend

# Expose Hugging Face spaces expected port
EXPOSE 7860

# Run FastAPI server
WORKDIR /app/backend
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
