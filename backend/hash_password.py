# hash_password.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_to_hash = "sifre123!" # Buraya kendi şifrenizi yazın
hashed_password = pwd_context.hash(password_to_hash)

print("Şifreniz:", password_to_hash)
print("Hash Hali:", hashed_password)
# Çıktıdaki hash'i .env dosyasına kopyalayın.