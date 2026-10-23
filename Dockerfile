FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements-dev.txt pytest.ini ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt
ENV FASTEMBED_CACHE_PATH=/app/models
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); TextEmbedding('intfloat/multilingual-e5-large')"
RUN python -c "from huggingface_hub import hf_hub_download; import os; dest='/app/models/nli'; os.makedirs(dest, exist_ok=True); repo='MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33'; [hf_hub_download(repo, name, local_dir=dest) for name in ('config.json','tokenizer.json','tokenizer_config.json','onnx/model_quantized.onnx')]"
ENV HF_HUB_OFFLINE=1
COPY backend /app/backend
COPY config /app/config
COPY evals /app/evals
COPY --from=web /web/dist /app/frontend/dist
ENV STATIC_DIR=/app/frontend/dist
ENV DATABASE_PATH=/app/data/receptionist.db
ENV PYTHONPATH=/app/backend:/app
ENV PYTHONUNBUFFERED=1
ENV DEMO_MODE=0
EXPOSE 43123
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "43123"]
