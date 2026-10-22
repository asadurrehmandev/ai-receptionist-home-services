FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /app/backend
COPY config /app/config
COPY --from=web /web/dist /app/frontend/dist
ENV STATIC_DIR=/app/frontend/dist
ENV DATABASE_PATH=/app/data/receptionist.db
ENV PYTHONUNBUFFERED=1
EXPOSE 43123
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "43123"]
