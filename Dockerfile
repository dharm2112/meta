# OpenEnv/Scaler evaluation Dockerfile
# Serves the environment via HTTP endpoints (reset, step, state)

FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ ./

# Set Python path
ENV PYTHONPATH=/app

# Expose port for OpenEnv HTTP requests
EXPOSE 7860

# Run the FastAPI server (OpenEnv calls /reset, /step, /state endpoints)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
