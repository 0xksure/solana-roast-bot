FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend /frontend/dist ./backend/static/
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
