# OpenEnv/Scaler evaluation Dockerfile
# Runs inference.py for automated benchmark evaluation

FROM python:3.11-slim

# Create non-root user for security
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install Python dependencies (minimal for inference)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY backend/ ./backend/

# Copy root-level files for OpenEnv
COPY inference.py ./
COPY openenv.yaml ./

# Set Python path to find backend modules
ENV PYTHONPATH=/app:/app/backend

# Add .pth file for reliable module resolution
RUN echo "/app" > "$(python -c 'import site; print(site.getsitepackages()[0])')/app.pth" && \
    echo "/app/backend" >> "$(python -c 'import site; print(site.getsitepackages()[0])')/app.pth"

# Switch to non-root user
USER appuser

# Default command: run inference with heuristic agent
CMD ["python", "inference.py", "--agent", "heuristic"]
