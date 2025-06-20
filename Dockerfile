# Temel olarak Python 3.11'in hafif bir sürümünü kullanıyoruz.
FROM python:3.11-slim

# Proje dosyalarının kopyalanacağı çalışma dizinini ayarlıyoruz.
WORKDIR /app

# Önce bağımlılıkları kopyalayıp kurarak Docker'ın katman önbellekleme mekanizmasından faydalanıyoruz.
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Projenin geri kalan tüm dosyalarını imajın içine kopyalıyoruz.
COPY . .

# Web arayüzünün çalışacağı portu dışarıya açıyoruz. 5001'i config.py'de değiştirebilirsiniz.
EXPOSE 5001

# Container başlatıldığında çalıştırılacak olan komut.
# Bu komut, arka plan servislerini ve web sunucusunu başlatacak olan yeni betiğimizi çalıştırır.
CMD ["python", "run.py"]