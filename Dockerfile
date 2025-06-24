# ==============================================================================
# File: Dockerfile (Projenin ana dizinindeki)
# @author: Memba Co.
# ==============================================================================
# --- 1. Aşama: Frontend Build Aşaması ---
    FROM node:18-alpine AS frontend-builder
    WORKDIR /app/frontend
    COPY frontend/package*.json ./
    RUN npm install
    COPY frontend/ ./
    RUN npm run build
    
    # --- 2. Aşama: Backend Aşaması ---
    FROM python:3.11-slim
    WORKDIR /app
    
    # Python bağımlılıklarını kuruyoruz.
    COPY backend/requirements.txt .
    RUN pip install --no-cache-dir --upgrade pip && \
        pip install --no-cache-dir -r requirements.txt
    
    # Tüm backend kodunu kopyalıyoruz.
    COPY backend/ .
    
    # Derlenmiş frontend dosyalarını backend'in sunacağı 'static' klasörüne kopyalıyoruz.
    COPY --from=frontend-builder /app/frontend/dist /app/static
    
    EXPOSE 8000
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]