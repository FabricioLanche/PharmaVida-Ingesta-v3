from fastapi import APIRouter, HTTPException
from app.orchestrator.docker_runner import DockerOrchestrator
import logging

router = APIRouter(prefix="/api/ingesta", tags=["Ingesta"])

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """
    Verifica el estado de salud del servicio.
    """
    try:
        orchestrator = DockerOrchestrator()
        return {
            "status": "healthy",
            "service": "ingesta-gateway",
            "docker_connection": "ok"
        }
    except Exception as e:
        logger.error(f"Health check falló: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Servicio no disponible: {str(e)}"
        )


@router.post("/mongodb")
async def run_mongodb_ingestion():
    """
    Ejecuta el script de ingesta de MongoDB en un contenedor efímero.

    Returns:
        Resultado de la ingesta con URLs de archivos en S3
    """
    try:
        logger.info("Iniciando ingesta de MongoDB...")
        orchestrator = DockerOrchestrator()
        result = await orchestrator.run_mongodb_script()

        if result["status"] == "error":
            logger.error(f"Error en ingesta MongoDB: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error desconocido")
            )

        logger.info("Ingesta de MongoDB completada exitosamente")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en MongoDB: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )


@router.post("/mysql")
async def run_mysql_ingestion():
    """
    Ejecuta el script de ingesta de MySQL en un contenedor efímero.

    Returns:
        Resultado de la ingesta con URLs de archivos en S3
    """
    try:
        logger.info("Iniciando ingesta de MySQL...")
        orchestrator = DockerOrchestrator()
        result = await orchestrator.run_mysql_script()

        if result["status"] == "error":
            logger.error(f"Error en ingesta MySQL: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error desconocido")
            )

        logger.info("Ingesta de MySQL completada exitosamente")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en MySQL: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )


@router.post("/postgresql")
async def run_postgresql_ingestion():
    """
    Ejecuta el script de ingesta de PostgreSQL en un contenedor efímero.

    Returns:
        Resultado de la ingesta con URLs de archivos en S3
    """
    try:
        logger.info("Iniciando ingesta de PostgreSQL...")
        orchestrator = DockerOrchestrator()
        result = await orchestrator.run_postgresql_script()

        if result["status"] == "error":
            logger.error(f"Error en ingesta PostgreSQL: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Error desconocido")
            )

        logger.info("Ingesta de PostgreSQL completada exitosamente")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en PostgreSQL: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error inesperado: {str(e)}"
        )