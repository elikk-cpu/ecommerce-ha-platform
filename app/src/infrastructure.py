import os

import boto3
import pika
import psycopg
from redis.sentinel import Sentinel


POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db-primary.ecom.test")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "ecommerce")
POSTGRES_USER = os.getenv("POSTGRES_USER", "ecommerce_app")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")


REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

REDIS_SENTINELS = [
    ("10.40.40.41", 26379),
    ("10.40.40.42", 26379),
    ("10.40.40.53", 26379),
]

REDIS_MASTER_NAME = os.getenv(
    "REDIS_MASTER_NAME",
    "ecommerce-master",
)


RABBITMQ_HOSTS = [
    "10.40.40.51",
    "10.40.40.52",
    "10.40.40.53",
]

RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "ecommerce_app")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/ecommerce")


MINIO_ENDPOINT = os.getenv(
    "MINIO_ENDPOINT",
    "http://10.40.40.61:9000",
)

MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "ecommerce")


def get_postgres_connection():
    return psycopg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def get_redis():
    sentinel = Sentinel(
        REDIS_SENTINELS,
        socket_timeout=2,
        password=REDIS_PASSWORD,
    )

    return sentinel.master_for(
        REDIS_MASTER_NAME,
        socket_timeout=2,
        password=REDIS_PASSWORD,
        decode_responses=True,
    )


def get_rabbitmq_connection():
    credentials = pika.PlainCredentials(
        RABBITMQ_USER,
        RABBITMQ_PASSWORD,
    )

    last_error = None

    for host in RABBITMQ_HOSTS:
        try:
            parameters = pika.ConnectionParameters(
                host=host,
                port=RABBITMQ_PORT,
                virtual_host=RABBITMQ_VHOST,
                credentials=credentials,
                connection_attempts=2,
                retry_delay=1,
            )

            return pika.BlockingConnection(parameters)

        except Exception as exc:
            last_error = exc

    raise RuntimeError(
        f"Unable to connect to RabbitMQ cluster: {last_error}"
    )


def get_minio_client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )
# infrastructure integration enabled
