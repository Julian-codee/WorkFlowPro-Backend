from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(
    title="Imagen 3D API",
    description=("Backend central para el ecosistema empresarial de Imagen 3D."),
    version="0.1.0",
)

app.include_router(
    api_router,
    prefix="/api/v1",
)


@app.get("/", tags=["Sistema"])
async def root():
    return {
        "application": "WorkFlowPro",
        "message": "API operativa",
        "documentation": "/docs",
    }
