import docker
from docker.errors import ContainerError, ImageNotFound, APIError
from typing import Dict, Any
from app.core.config import settings
import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DockerOrchestrator:
    def __init__(self):
        try:
            self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
            self.client.ping()
        except Exception as e:
            raise RuntimeError(f"No se pudo conectar al Docker daemon: {str(e)}")

    def _get_common_env(self) -> Dict[str, str]:
        """Variables de entorno comunes para AWS."""
        return {
            "AWS_BUCKET_NAME": settings.AWS_BUCKET_NAME,
            "AWS_REGION": settings.AWS_REGION,
            "AWS_PROFILE": "default",
            "AWS_SHARED_CREDENTIALS_FILE": "/root/.aws/credentials",
            "AWS_CONFIG_FILE": "/root/.aws/config"
        }

    def _get_aws_volume(self) -> Dict[str, Any]:
        """Monta el volumen de credenciales AWS desde el host."""
        # Primero intentar desde la variable de entorno
        aws_credentials_path = os.getenv("AWS_CREDENTIALS_HOST_PATH", "/home/ubuntu/.aws")
        
        logger.info(f"Intentando montar credenciales AWS desde: {aws_credentials_path}")
        
        # Verificar que la ruta existe en el HOST
        # Si estamos en un contenedor, intentar encontrar la ruta montada
        possible_paths = [
            aws_credentials_path,  # Ruta del .env
            "/root/.aws",  # Ruta dentro del contenedor API
            str(Path.home() / ".aws"),
            os.path.expanduser("~/.aws")
        ]
        
        host_aws_path = None
        for path in possible_paths:
            credentials_file = os.path.join(path, "credentials")
            if os.path.exists(credentials_file):
                host_aws_path = path
                logger.info(f"✓ Credenciales AWS encontradas en: {host_aws_path}")
                break
        
        if not host_aws_path:
            raise RuntimeError(
                f"No se encontraron credenciales AWS. Buscado en: {possible_paths}. "
                f"Por favor, asegúrate de que {aws_credentials_path}/credentials existe en el host "
                f"o que las credenciales estén montadas en el contenedor API."
            )
        
        # Si encontramos las credenciales en /root/.aws (contenedor API),
        # necesitamos usar la ruta del HOST original
        if host_aws_path == "/root/.aws":
            # Estamos en un contenedor, usar la ruta del host
            host_aws_path = aws_credentials_path
            logger.info(f"Usando ruta del host para montar en contenedores hijos: {host_aws_path}")
        
        # Montar la carpeta .aws del host en /root/.aws del contenedor (read-only)
        return {host_aws_path: {"bind": "/root/.aws", "mode": "ro"}}

    def _parse_container_output(self, output: bytes) -> Dict[str, Any]:
        """Parsea la salida del contenedor."""
        try:
            output_str = output.decode('utf-8').strip()
            
            # Log para debugging
            logger.debug(f"Output del contenedor: {output_str}")
            
            # Intentar parsear como JSON
            return json.loads(output_str)
        except json.JSONDecodeError:
            logger.warning(f"No se pudo parsear como JSON: {output_str}")
            return {"output": output_str}
        except Exception as e:
            logger.error(f"Error parseando salida: {str(e)}")
            return {"error": f"Error parseando salida: {str(e)}", "raw_output": str(output)}

    def _run_container(self, image: str, env_vars: Dict[str, str], database: str) -> Dict[str, Any]:
        """Método genérico para ejecutar contenedores con manejo de errores mejorado."""
        try:
            volumes = self._get_aws_volume()
            
            logger.info(f"Ejecutando contenedor {image}")
            logger.info(f"Red: {settings.DOCKER_NETWORK}")
            logger.info(f"Variables de entorno: {list(env_vars.keys())}")
            
            # Ejecutar contenedor y capturar logs
            container = self.client.containers.run(
                image=image,
                environment=env_vars,
                network=settings.DOCKER_NETWORK,
                remove=False,  # No remover automáticamente para poder ver logs
                detach=True,
                volumes=volumes
            )
            
            # Esperar a que termine
            result = container.wait()
            
            # Obtener logs
            logs = container.logs().decode('utf-8')
            logger.info(f"Logs del contenedor {database}:\n{logs}")
            
            # Remover contenedor
            container.remove()
            
            # Verificar código de salida
            if result['StatusCode'] != 0:
                error_msg = f"El contenedor retornó código {result['StatusCode']}"
                logger.error(f"{error_msg}\nLogs:\n{logs}")
                return {
                    "status": "error",
                    "database": database,
                    "error": error_msg,
                    "logs": logs
                }
            
            # Parsear resultado
            parsed_result = self._parse_container_output(logs.encode('utf-8'))
            return {"status": "success", "database": database, "result": parsed_result}
            
        except ImageNotFound:
            error_msg = f"Imagen {image} no encontrada. Ejecuta: docker build -t {image} ./scripts/{database}"
            logger.error(error_msg)
            return {"status": "error", "database": database, "error": error_msg}
        except RuntimeError as e:
            logger.error(f"RuntimeError en {database}: {str(e)}")
            return {"status": "error", "database": database, "error": str(e)}
        except ContainerError as e:
            logger.error(f"ContainerError en {database}: {str(e)}")
            return {"status": "error", "database": database, "error": f"Error en contenedor: {str(e)}"}
        except APIError as e:
            logger.error(f"APIError en {database}: {str(e)}")
            return {"status": "error", "database": database, "error": f"Error de Docker API: {str(e)}"}
        except Exception as e:
            logger.error(f"Error inesperado en {database}: {str(e)}", exc_info=True)
            return {"status": "error", "database": database, "error": f"Error inesperado: {str(e)}"}

    async def run_mongodb_script(self) -> Dict[str, Any]:
        env_vars = self._get_common_env()
        env_vars.update({
            "MONGO_HOST": settings.MONGO_HOST,
            "MONGO_PORT": str(settings.MONGO_PORT),
            "MONGO_USER": settings.MONGO_USER,
            "MONGO_PASSWORD": settings.MONGO_PASSWORD,
            "MONGO_DATABASE": settings.MONGO_DATABASE,
        })
        return self._run_container("pharmavida-ingesta-mongodb:latest", env_vars, "mongodb")

    async def run_mysql_script(self) -> Dict[str, Any]:
        env_vars = self._get_common_env()
        env_vars.update({
            "MYSQL_HOST": settings.MYSQL_HOST,
            "MYSQL_PORT": str(settings.MYSQL_PORT),
            "MYSQL_USER": settings.MYSQL_USER,
            "MYSQL_PASSWORD": settings.MYSQL_PASSWORD,
            "MYSQL_DATABASE": settings.MYSQL_DATABASE,
        })
        return self._run_container("pharmavida-ingesta-mysql:latest", env_vars, "mysql")

    async def run_postgresql_script(self) -> Dict[str, Any]:
        env_vars = self._get_common_env()
        env_vars.update({
            "POSTGRES_HOST": settings.POSTGRES_HOST,
            "POSTGRES_PORT": str(settings.POSTGRES_PORT),
            "POSTGRES_USER": settings.POSTGRES_USER,
            "POSTGRES_PASSWORD": settings.POSTGRES_PASSWORD,
            "POSTGRES_DATABASE": settings.POSTGRES_DATABASE,
        })
        return self._run_container("pharmavida-ingesta-postgresql:latest", env_vars, "postgresql")