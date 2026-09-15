import os
import socket
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    generate_latest,
)
from pydantic import BaseModel, Field

from src.checkout import process_checkout
from src.infrastructure import (
    MINIO_BUCKET,
    get_minio_client,
    get_postgres_connection,
    get_rabbitmq_connection,
    get_redis,
)

app = FastAPI(
    title="Ecommerce HA Platform",
    version="0.3.0",
)

HOSTNAME = socket.gethostname()
APP_ENV = os.getenv("APP_ENV", "production")


REQUESTS_TOTAL = Counter(
    "ecommerce_http_requests_total",
    "Total number of HTTP requests",
    ["endpoint"],
)

CHECKOUTS_TOTAL = Counter(
    "ecommerce_checkouts_total",
    "Total number of checkout requests",
    ["result"],
)


class CheckoutRequest(BaseModel):
    customer: str = Field(
        min_length=1,
        max_length=100,
    )
    amount: Decimal = Field(gt=0)


def check_postgresql() -> bool:
    connection = None

    try:
        connection = get_postgres_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return True

    except Exception:
        return False

    finally:
        if connection is not None:
            connection.close()


def check_redis() -> bool:
    try:
        return bool(get_redis().ping())

    except Exception:
        return False


def check_rabbitmq() -> bool:
    connection = None

    try:
        connection = get_rabbitmq_connection()
        return connection.is_open

    except Exception:
        return False

    finally:
        if connection is not None and connection.is_open:
            connection.close()


def check_minio() -> bool:
    try:
        client = get_minio_client()
        client.head_bucket(Bucket=MINIO_BUCKET)
        return True

    except Exception:
        return False


@app.get("/")
def root():
    REQUESTS_TOTAL.labels(endpoint="/").inc()

    return {
        "service": "ecommerce-api",
        "instance": HOSTNAME,
        "environment": APP_ENV,
        "status": "running",
    }


@app.get("/health")
def health():
    REQUESTS_TOTAL.labels(endpoint="/health").inc()

    return {
        "status": "ok",
        "instance": HOSTNAME,
    }


@app.get("/ready")
def ready():
    REQUESTS_TOTAL.labels(endpoint="/ready").inc()

    checks = {
        "postgresql": check_postgresql(),
        "redis": check_redis(),
        "rabbitmq": check_rabbitmq(),
        "minio": check_minio(),
    }

    is_ready = all(checks.values())

    payload = {
        "status": "ready" if is_ready else "not_ready",
        "instance": HOSTNAME,
        "checks": checks,
    }

    if not is_ready:
        return JSONResponse(
            status_code=503,
            content=payload,
        )

    return payload


@app.post("/checkout", status_code=201)
def checkout(request: CheckoutRequest):
    REQUESTS_TOTAL.labels(endpoint="/checkout").inc()

    try:
        order = process_checkout(
            customer=request.customer,
            amount=request.amount,
        )

        CHECKOUTS_TOTAL.labels(result="success").inc()

        return {
            **order,
            "instance": HOSTNAME,
        }

    except Exception:
        CHECKOUTS_TOTAL.labels(result="failure").inc()

        raise HTTPException(
            status_code=503,
            detail="Checkout dependency failure",
        ) from None

@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
