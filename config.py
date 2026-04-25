import os

USUARIO_ADMIN = os.environ.get("USUARIO_ADMIN", "admin")
PASSWORD_ADMIN = os.environ.get("PASSWORD_ADMIN", "1234")
SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esto-por-una-clave-segura")
DATABASE_URL = os.environ.get("DATABASE_URL")