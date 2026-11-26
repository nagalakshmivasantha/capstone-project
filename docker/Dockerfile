FROM node:22-bookworm-slim AS dashboard
WORKDIR /dashboard
COPY app/frontend/package*.json ./
RUN npm ci
COPY app/frontend/index.html app/frontend/vite.config.js ./
COPY app/frontend/src ./src
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
COPY --from=dashboard /dashboard/dist /app/app/frontend/dist
EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
