from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import ErrorResponse
from app.core.middleware import JsonCORS, RequestSafety
from app.core.settings import Settings, database_url
from app.modules.projects.router import router
from app.telemetry.setup import configure_telemetry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = create_engine(
        database_url(settings.database_url),
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        connect_args={"connect_timeout": 3},
    )
    telemetry = configure_telemetry(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()
        telemetry.shutdown()

    app = FastAPI(
        title="BuildWise API",
        version="0.1.0",
        lifespan=lifespan,
        responses={
            status: {"model": ErrorResponse}
            for status in (400, 404, 405, 413, 422, 429, 500, 503)
        },
    )
    app.state.engine = engine

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = str(exc.detail) if exc.status_code < 500 else "Service unavailable"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "database_unavailable"
                    if exc.status_code == 503
                    else f"http_{exc.status_code}",
                    "message": message,
                    "correlation_id": request.state.correlation_id,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Invalid request",
                    "correlation_id": request.state.correlation_id,
                }
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> dict[str, str]:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise HTTPException(503, "Database unavailable") from exc
        return {"status": "ready"}

    app.include_router(router)
    app.add_middleware(
        JsonCORS,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Correlation-ID", "X-Project-Token"],
        expose_headers=["X-Correlation-ID"],
    )
    app.add_middleware(RequestSafety)
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=telemetry.traces,
        meter_provider=telemetry.metrics,
    )
    SQLAlchemyInstrumentor().instrument(engine=engine, tracer_provider=telemetry.traces)
    return app
