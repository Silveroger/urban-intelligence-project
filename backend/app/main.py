import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.security import setup_cors
from app.core.errors import (
    BaseAPIException,
    DatabaseConnectionError,
    custom_api_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    database_exception_handler,
    unhandled_exception_handler,
    get_current_iso_timestamp,
)
from sqlalchemy.exc import SQLAlchemyError
from app.db.database import engine, check_database_connection
from app.api.v1 import api_v1_router
from app.websocket.live import router as websocket_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("urban_intel.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SIH 26124 Urban Intelligence Platform Backend...")
    yield
    logger.info("Shutting down database connection engine...")
    await engine.dispose()


app = FastAPI(
    title="Urban Intelligence Platform API",
    description="AI-Powered Mobile Urban Intelligence Platform Using Public Transport Fleet (SIH 26124)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 1. Setup CORS
setup_cors(app)

# 2. Register Custom Exception Handlers (contract-compliant errors)
app.add_exception_handler(BaseAPIException, custom_api_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# 3. Mount Routers
app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/ws")


# 4. System Health Endpoints
@app.get("/", tags=["System"])
async def root():
    return {
        "service": "SIH 26124 Urban Intelligence Platform API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "database_health": "/health/database",
    }


@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "ok",
        "timestamp": get_current_iso_timestamp(),
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/database", tags=["System"])
async def database_health_check():
    db_status = await check_database_connection()
    return {
        "timestamp": get_current_iso_timestamp(),
        "database": db_status,
    }
