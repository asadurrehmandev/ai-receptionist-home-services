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
COPY backend /app/backend
COPY config /app/config
COPY --from=web /web/dist /app/frontend/dist
ENV STATIC_DIR=/app/frontend/dist
ENV DATABASE_PATH=/app/data/receptionist.db
ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1
ENV DEMO_MODE=0
EXPOSE 43123
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "43123"]
