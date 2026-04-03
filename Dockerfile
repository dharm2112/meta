FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY env/ env/
COPY generator/ generator/
COPY grader/ grader/
COPY tasks/ tasks/
COPY baseline.py inference.py openenv.yaml app.py ./

RUN pip install --no-cache-dir ".[ui]"

EXPOSE 7860

ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

CMD ["python", "app.py"]
