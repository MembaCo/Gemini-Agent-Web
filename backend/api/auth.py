# ==============================================================================
# File: backend/api/auth.py
# @author: Memba Co.
# ==============================================================================
import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from core.security import verify_password, create_access_token

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Kullanıcı adı ve şifre ile JWT access token oluşturur.
    FastAPI'nin OAuth2PasswordRequestForm'u, 'username' ve 'password'
    alanlarını form verisinden otomatik olarak alır.
    """
    admin_user = os.getenv("ADMIN_USERNAME")
    admin_pass_hash = os.getenv("ADMIN_PASSWORD_HASH")

    if not admin_user or not admin_pass_hash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin credentials are not configured on the server."
        )

    is_password_correct = verify_password(form_data.password, admin_pass_hash)
    
    if not (form_data.username == admin_user and is_password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=60 * 24) # 24 saat
    access_token = create_access_token(
        data={"sub": admin_user}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}