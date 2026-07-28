import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY não definida. Crie um arquivo .env com SECRET_KEY=seu-valor-aqui")
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bar_adega.db")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_DEBUG", "0") != "1"
    PERMANENT_SESSION_LIFETIME = 3600 * 4
