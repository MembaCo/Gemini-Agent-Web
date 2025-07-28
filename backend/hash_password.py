# backend/hash_password.py
import sys
from getpass import getpass
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

try:
    # Parolayı güvenli bir şekilde iste
    password_to_hash = getpass("Lütfen hash'lenecek şifreyi girin: ")
    if not password_to_hash:
        print("Şifre boş olamaz.")
        sys.exit(1)
        
    hashed_password = pwd_context.hash(password_to_hash)
    print("\nOluşturulan Hash Değeri:")
    print(hashed_password)
    print("\nBu değeri .env dosyanızdaki ADMIN_PASSWORD_HASH alanına kopyalayın.")

except KeyboardInterrupt:
    print("\nİşlem iptal edildi.")
    sys.exit(0)