import os
import socket

from fastapi import FastAPI, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST


app = FastAPI(
    title="Ecommerce HA Platform",
    version="0.1.0",
)

HOSTNAME = socket.gethostname()
APP_ENV = os.getenv("APP_ENV", "production")

REQUESTS_TOTAL = Counter(
    "ecommerce_http_requests_total",
    "Total number of HTTP requests",
    ["endpoint"],
)


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

    return {
        "status": "ready",
        "instance": HOSTNAME,
    }


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
