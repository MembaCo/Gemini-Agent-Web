# Stage 1: Build React frontend
# Bu aşama, React kodunu statik HTML, CSS ve JS dosyalarına dönüştürür.
FROM node:18-alpine as builder
WORKDIR /app/frontend
# Sadece package.json dosyalarını kopyala ve bağımlılıkları yükle
COPY frontend/package*.json ./
RUN npm install
# Frontend kodunun tamamını kopyala ve build et
COPY frontend/ .
RUN npm run build

# Stage 2: Setup Python backend
# Bu aşama, Python sunucusunu kurar ve frontend'den gelen statik dosyaları içine alır.
FROM python:3.11-slim
WORKDIR /app

# Önce bağımlılıkları kopyalayıp kurarak Docker katman önbelleğinden faydalanıyoruz.
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Frontend build'ini backend'in static klasörüne kopyala
# Bu, sunucunun web arayüzünü sunabilmesini sağlar.
COPY --from=builder /app/frontend/dist ./backend/static

# Backend kodunun tamamını kopyala
COPY backend/ ./backend/

# YENİ: Merkezi versiyon dosyasını kopyala
# Bu, versiyon uyarılarını giderir.
COPY VERSION .

# Uygulamanın çalışacağı port
EXPOSE 8000

# Konteyner başladığında çalıştırılacak komut
# Çalışma dizinini backend olarak ayarla ve sunucuyu başlat
WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
