import boto3
import os
from datetime import datetime
import io
import sys
import json


class S3Uploader:
    def __init__(self):
        self.bucket_name = os.getenv("AWS_BUCKET_NAME")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        # Verificar que existe el archivo de credenciales
        credentials_file = "/root/.aws/credentials"
        if not os.path.exists(credentials_file):
            raise RuntimeError(
                f"Archivo de credenciales no encontrado en {credentials_file}. "
                f"Asegúrate de que el volumen esté montado correctamente."
            )
        
        # Verificar permisos de lectura
        if not os.access(credentials_file, os.R_OK):
            raise RuntimeError(
                f"No hay permisos de lectura en {credentials_file}"
            )
        
        # Leer y verificar contenido (sin mostrar credenciales)
        try:
            with open(credentials_file, 'r') as f:
                content = f.read()
                if not content.strip():
                    raise RuntimeError("El archivo de credenciales está vacío")
                if '[default]' not in content:
                    raise RuntimeError("No se encontró el perfil [default] en credenciales")
                print("✓ Credenciales AWS encontradas y con formato válido", file=sys.stderr)
        except Exception as e:
            raise RuntimeError(f"Error leyendo credenciales: {str(e)}")
        
        # Configurar boto3 explícitamente
        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = credentials_file
        os.environ["AWS_CONFIG_FILE"] = "/root/.aws/config"
        os.environ["AWS_PROFILE"] = "default"
        
        try:
            # Crear sesión usando el perfil explícito
            session = boto3.Session(profile_name='default')
            self.s3_client = session.client('s3', region_name=self.region)
            
            # Verificar credenciales haciendo una llamada simple
            self.s3_client.list_buckets()
            print(f"✓ Conexión exitosa a AWS S3 en región {self.region}", file=sys.stderr)
            
        except Exception as e:
            raise RuntimeError(f"Error al crear cliente S3: {str(e)}")

    def upload_json(self, json_content: str, database_name: str, collection_name: str) -> str:
        """
        Sube un archivo JSON al bucket S3 organizado por carpetas de base de datos

        Args:
            json_content: Contenido JSON como string
            database_name: Nombre de la base de datos (mongodb)
            collection_name: Nombre de la colección

        Returns:
            URL del archivo subido
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{database_name}/{collection_name}_{timestamp}.json"

        json_buffer = io.BytesIO(json_content.encode('utf-8'))

        try:
            self.s3_client.upload_fileobj(
                json_buffer,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': 'application/json'}
            )
            print(f"✓ Archivo JSON subido exitosamente: {s3_key}", file=sys.stderr)
        except Exception as e:
            raise RuntimeError(f"Error subiendo archivo JSON a S3: {str(e)}")

        s3_url = f"s3://{self.bucket_name}/{s3_key}"
        return s3_url

    def upload_documents(self, documents: list, database_name: str, collection_name: str) -> str:
        """
        Sube documentos de MongoDB como JSON al bucket S3

        Args:
            documents: Lista de documentos (dicts) de MongoDB
            database_name: Nombre de la base de datos
            collection_name: Nombre de la colección

        Returns:
            URL del archivo subido
        """
        try:
            # Convertir documentos a JSON string (pretty print para legibilidad)
            json_content = json.dumps(documents, indent=2, default=str, ensure_ascii=False)
            return self.upload_json(json_content, database_name, collection_name)
        except Exception as e:
            raise RuntimeError(f"Error convirtiendo documentos a JSON: {str(e)}")

    def upload_csv(self, csv_content: str, database_name: str, collection_name: str) -> str:
        """
        Sube un CSV al bucket S3 (alternativa para compatibilidad)

        Args:
            csv_content: Contenido del CSV como string
            database_name: Nombre de la base de datos
            collection_name: Nombre de la colección

        Returns:
            URL del archivo subido
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{database_name}/{collection_name}_{timestamp}.csv"

        csv_buffer = io.BytesIO(csv_content.encode('utf-8'))

        try:
            self.s3_client.upload_fileobj(
                csv_buffer,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': 'text/csv'}
            )
            print(f"✓ Archivo CSV subido exitosamente: {s3_key}", file=sys.stderr)
        except Exception as e:
            raise RuntimeError(f"Error subiendo archivo CSV a S3: {str(e)}")

        s3_url = f"s3://{self.bucket_name}/{s3_key}"
        return s3_url

    def upload_dataframe(self, df, database_name: str, collection_name: str) -> str:
        """
        Sube un DataFrame de pandas como JSON al bucket S3 (para MongoDB)

        Args:
            df: DataFrame de pandas
            database_name: Nombre de la base de datos
            collection_name: Nombre de la colección

        Returns:
            URL del archivo subido
        """
        # Convertir DataFrame a lista de documentos (registros)
        documents = df.to_dict('records')
        
        # Usar el método upload_documents para subir como JSON
        return self.upload_documents(documents, database_name, collection_name)