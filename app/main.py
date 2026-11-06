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


@app.get("api/v1/health", tags=["Sistema"])
async def health_check():
    return {
        "status": "ok",
        "application": "WorkFlowPro",
        "message": "Backend funcionando correctamente",
        "api_version": "v1",
    }