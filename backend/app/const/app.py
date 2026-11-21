DEVELOPMENT_ENV = "development"
STARTUP_LOGGER_NAME = "uvicorn.error"
INSECURE_JWT_SECRET_MESSAGE = "JWT_SECRET_KEY must be set to a real secret when APP_ENV is not 'development'"

DEFAULT_CORS_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

HEALTH_STATUS_OK = "ok"
HEALTH_PATH = "/health"
API_HEALTH_PATH = "/api/health"
DB_SESSION_SCOPE = "function"
