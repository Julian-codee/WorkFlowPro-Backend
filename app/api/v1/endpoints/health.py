from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    tags=["Sistema"],
    summary="Comprobar estado de la API",
)
async def health_check():
    return {
        "status": "healthy",
        "application": "Imagen 3D Backend",
        "version": "0.1.0",
    }