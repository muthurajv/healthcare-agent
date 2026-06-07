from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from api.routers import appointments
from observability.tracing import init_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_tracing()
    yield


app = FastAPI(
    title="HCSC Healthcare Member Agent",
    description="Agentic AI for finding in-network specialists and scheduling appointments",
    version="0.1.0",
    lifespan=lifespan,
)

FastAPIInstrumentor.instrument_app(app)

app.include_router(appointments.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
