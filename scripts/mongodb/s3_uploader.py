import boto3
import os
from datetime import datetime
import io
import sys


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

    def upload_csv(self, csv_content: str, database_name: str, table_name: str) -> str:
        """
        Sube un CSV al bucket S3 organizado por carpetas de base de datos

        Args:
            csv_content: Contenido del CSV como string
            database_name: Nombre de la base de datos (mongodb, postgresql, mysql)
            table_name: Nombre de la tabla o colección

        Returns:
            URL del archivo subido
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_key = f"{database_name}/{table_name}_{timestamp}.csv"

        csv_buffer = io.BytesIO(csv_content.encode('utf-8'))

        try:
            self.s3_client.upload_fileobj(
                csv_buffer,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': 'text/csv'}
            )
            print(f"✓ Archivo subido exitosamente: {s3_key}", file=sys.stderr)
        except Exception as e:
            raise RuntimeError(f"Error subiendo archivo a S3: {str(e)}")

        s3_url = f"s3://{self.bucket_name}/{s3_key}"
        return s3_url

    def upload_dataframe(self, df, database_name: str, table_name: str) -> str:
        """
        Sube un DataFrame de pandas como CSV al bucket S3

        Args:
            df: DataFrame de pandas
            database_name: Nombre de la base de datos
            table_name: Nombre de la tabla o colección

        Returns:
            URL del archivo subido
        """
        csv_content = df.to_csv(index=False)
        return self.upload_csv(csv_content, database_name, table_name)