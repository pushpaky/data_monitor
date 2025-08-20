import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "aquesa_management")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "raw_data_ts")

# Email Configuration
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# Device Email Mapping
try:
    DEVICE_EMAIL_MAP = json.loads(os.getenv("DEVICE_EMAIL_MAP", "{}"))
except json.JSONDecodeError:
    DEVICE_EMAIL_MAP = {}

# Scheduling Configuration
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "08:00")
TIMEZONE = os.getenv("TIMEZONE", "UTC")

# Application Settings
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Performance Settings
MONGO_MAX_POOL_SIZE = int(os.getenv("MONGO_MAX_POOL_SIZE", "10"))
MONGO_MIN_POOL_SIZE = int(os.getenv("MONGO_MIN_POOL_SIZE", "2"))
THREAD_POOL_WORKERS = int(os.getenv("THREAD_POOL_WORKERS", "4"))
CHART_DPI = int(os.getenv("CHART_DPI", "200"))
MAX_RECORDS_LIMIT = int(os.getenv("MAX_RECORDS_LIMIT", "10000"))

# Security Settings
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Monitoring Settings
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "10"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
