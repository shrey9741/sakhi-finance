from fastapi import FastAPI

from app.api.v1 import health

app = FastAPI(title="Sakhi Finance API", version="0.1.0")
app.include_router(health.router, prefix="/api/v1")