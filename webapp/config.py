import os

from savant.config import get_db_path


class Config:
    DATABASE_PATH = get_db_path()
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-key-change-in-prod")


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True
