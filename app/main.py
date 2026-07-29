import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.api.v1 import health
from app.api.v1 import users
from app.api.v1 import queries
from app.core.exceptions import global_exception_handler
from app.db.qdrant import init_qdrant

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    await init_qdrant()
    yield
    # Shutdown actions could go here

app = FastAPI(
    title="Agentic Research Assistant",
    version="0.1.0",
    description="Production‑grade AI research assistant",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_exception_handler(Exception, global_exception_handler)

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(queries.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to the Agentic Research Assistant API"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(settings.port), reload=True)
