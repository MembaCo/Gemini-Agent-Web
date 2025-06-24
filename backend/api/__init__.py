# backend/api/__init__.py
# @author: Memba Co.

# Bu dosya, 'api' klasörünün bir Python paketi olarak tanınmasını sağlar
# ve içindeki tüm router'ları dışarıya sunar.

from .analysis import router as analysis_router
from .dashboard import router as dashboard_router
from .positions import router as positions_router
from .scanner import router as scanner_router
from .settings import router as settings_router
