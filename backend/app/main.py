from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.datasets import router as dataset_router
from app.api.routes import router
from app.config import Settings, get_settings
from app.database import DuckDBManager
from app.datasets.errors import DatasetError


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    database = DuckDBManager(active_settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        database.initialize()
        yield

    application = FastAPI(
        title="Koies Process Mining API",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.settings = active_settings
    application.state.database = database
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Accept", "Content-Type"],
    )
    application.add_exception_handler(
        DatasetError,
        lambda _request, error: JSONResponse(
            status_code=error.status_code,
            content={"detail": {"code": error.code, "message": error.message}},
        ),
    )
    application.include_router(router)
    application.include_router(dataset_router)
    return application


app = create_app()
