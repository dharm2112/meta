# OpenEnv/Scaler evaluation Dockerfile
# Runs inference with LiteLLM proxy for Phase 2 validation

FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code
COPY backend/ ./backend/
COPY inference.py ./

# Set Python path
ENV PYTHONPATH=/app:/app/backend

# Run inference with LLM agent (uses API_KEY and API_BASE_URL from environment)
CMD ["python", "inference.py", "--agent", "llm"]
