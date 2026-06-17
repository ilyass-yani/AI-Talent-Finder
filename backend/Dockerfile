FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev tesseract-ocr tesseract-ocr-fra poppler-utils \
 && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PYTHONUNBUFFERED=1
ENV HF_HOME=/home/user/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/home/user/.cache/sentence-transformers \
    TORCH_HOME=/home/user/.cache/torch
WORKDIR /app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .
USER user
EXPOSE 7860
ENTRYPOINT ["bash", "docker-entrypoint.sh"]
