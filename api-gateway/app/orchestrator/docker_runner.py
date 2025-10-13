import docker
from docker.errors import ContainerError, ImageNotFound, APIError
from typing import Dict, Any
from app.core.config import settings
import json
import os


class DockerOrchestrator:
    def __init__(self):
        try:
            self.client = docker.DockerClient(base_url='unix://var/run/docker.sock')
            self.client.ping()
        except Exception as e:
            raise RuntimeError(f"No se pudo conectar al Docker daemon: {str(e)}")

    def _get_common_env(self) -> Dict[str, str]:
        """Variables de entorno comunes (sin credenciales AWS explícitas)."""
        return {
            "AWS_BUCKET_NAME": settings.AWS_BUCKET_NAME,
            "AWS_REGION": settings.AWS_REGION
        }

    def _get_aws_volume(self):
        aws_path = os.environ.get("AWS_CREDENTIALS_HOST_PATH", os.path.expanduser("~/.aws"))
        return {aws_path: {"bind": "/root/.aws", "mode": "ro"}}

    def _parse_container_output(self, output: bytes) -> Dict[str, Any]:
        """Parsea la salida del contenedor."""
        try:
            output_str = output.decode('utf-8').strip()
            return json.loads(output_str)
        except json.JSONDecodeError:
            return {"output": output_str}
        except Exception as e:
            return {"error": f"Error parseando salida: {str(e)}", "raw_output": output_str}

    async def run_mongodb_script(self) -> Dict[str, Any]:
        try:
            env_vars = self._get_common_env()
            env_vars.update({
                "MONGO_HOST": settings.MONGO_HOST,
                "MONGO_PORT": str(settings.MONGO_PORT),
                "MONGO_USER": settings.MONGO_USER,
                "MONGO_PASSWORD": settings.MONGO_PASSWORD,
                "MONGO_DATABASE": settings.MONGO_DATABASE,
            })

            container = self.client.containers.run(
                image="pharmavida-ingesta-mongodb:latest",
                environment=env_vars,
                network=settings.DOCKER_NETWORK,
                remove=True,
                detach=False,
                volumes=self._get_aws_volume()
            )

            result = self._parse_container_output(container)
            return {"status": "success", "database": "mongodb", "result": result}

        except ImageNotFound:
            return {"status": "error", "database": "mongodb",
                    "error": "Imagen pharmavida-ingesta-mongodb:latest no encontrada. Ejecuta: docker build -t pharmavida-ingesta-mongodb:latest ./scripts/mongodb"}
        except ContainerError as e:
            return {"status": "error", "database": "mongodb", "error": str(e)}
        except APIError as e:
            return {"status": "error", "database": "mongodb", "error": str(e)}
        except Exception as e:
            return {"status": "error", "database": "mongodb", "error": str(e)}

    async def run_mysql_script(self) -> Dict[str, Any]:
        try:
            env_vars = self._get_common_env()
            env_vars.update({
                "MYSQL_HOST": settings.MYSQL_HOST,
                "MYSQL_PORT": str(settings.MYSQL_PORT),
                "MYSQL_USER": settings.MYSQL_USER,
                "MYSQL_PASSWORD": settings.MYSQL_PASSWORD,
                "MYSQL_DATABASE": settings.MYSQL_DATABASE,
            })

            container = self.client.containers.run(
                image="pharmavida-ingesta-mysql:latest",
                environment=env_vars,
                network=settings.DOCKER_NETWORK,
                remove=True,
                detach=False,
                volumes=self._get_aws_volume()
            )

            result = self._parse_container_output(container)
            return {"status": "success", "database": "mysql", "result": result}

        except ImageNotFound:
            return {"status": "error", "database": "mysql",
                    "error": "Imagen pharmavida-ingesta-mysql:latest no encontrada. Ejecuta: docker build -t pharmavida-ingesta-mysql:latest ./scripts/mysql"}
        except ContainerError as e:
            return {"status": "error", "database": "mysql", "error": str(e)}
        except APIError as e:
            return {"status": "error", "database": "mysql", "error": str(e)}
        except Exception as e:
            return {"status": "error", "database": "mysql", "error": str(e)}

    async def run_postgresql_script(self) -> Dict[str, Any]:
        try:
            env_vars = self._get_common_env()
            env_vars.update({
                "POSTGRES_HOST": settings.POSTGRES_HOST,
                "POSTGRES_PORT": str(settings.POSTGRES_PORT),
                "POSTGRES_USER": settings.POSTGRES_USER,
                "POSTGRES_PASSWORD": settings.POSTGRES_PASSWORD,
                "POSTGRES_DATABASE": settings.POSTGRES_DATABASE,
            })

            container = self.client.containers.run(
                image="pharmavida-ingesta-postgresql:latest",
                environment=env_vars,
                network=settings.DOCKER_NETWORK,
                remove=True,
                detach=False,
                volumes=self._get_aws_volume()
            )

            result = self._parse_container_output(container)
            return {"status": "success", "database": "postgresql", "result": result}

        except ImageNotFound:
            return {"status": "error", "database": "postgresql",
                    "error": "Imagen pharmavida-ingesta-postgresql:latest no encontrada. Ejecuta: docker build -t pharmavida-ingesta-postgresql:latest ./scripts/postgresql"}
        except ContainerError as e:
            return {"status": "error", "database": "postgresql", "error": str(e)}
        except APIError as e:
            return {"status": "error", "database": "postgresql", "error": str(e)}
        except Exception as e:
            return {"status": "error", "database": "postgresql", "error": str(e)}
