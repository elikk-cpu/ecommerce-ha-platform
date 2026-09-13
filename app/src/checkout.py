import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pika

from src.infrastructure import (
    MINIO_BUCKET,
    get_minio_client,
    get_postgres_connection,
    get_rabbitmq_connection,
    get_redis,
)


def ensure_orders_table() -> None:
    connection = get_postgres_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id UUID PRIMARY KEY,
                    customer VARCHAR(100) NOT NULL,
                    amount NUMERIC(12, 2) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )

        connection.commit()

    finally:
        connection.close()


def mark_order_failed(order_id: str) -> None:
    connection = get_postgres_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE orders
                SET status = 'integration_error'
                WHERE id = %s
                """,
                (order_id,),
            )

        connection.commit()

    finally:
        connection.close()


def process_checkout(customer: str, amount: Decimal) -> dict:
    ensure_orders_table()

    order_id = str(uuid4())
    created_at = datetime.now(timezone.utc)
    amount_text = f"{amount:.2f}"

    connection = get_postgres_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO orders (
                    id,
                    customer,
                    amount,
                    status,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    order_id,
                    customer,
                    amount,
                    "created",
                    created_at,
                ),
            )

        connection.commit()

    finally:
        connection.close()

    payload = {
        "order_id": order_id,
        "customer": customer,
        "amount": amount_text,
        "status": "created",
        "created_at": created_at.isoformat(),
    }

    try:
        redis_client = get_redis()

        redis_client.setex(
            f"order:{order_id}",
            3600,
            json.dumps(payload),
        )

        rabbitmq_connection = get_rabbitmq_connection()

        try:
            channel = rabbitmq_connection.channel()
            channel.confirm_delivery()

            channel.basic_publish(
                exchange="orders",
                routing_key="order.created",
                body=json.dumps(payload).encode(),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )

        finally:
            if rabbitmq_connection.is_open:
                rabbitmq_connection.close()

        minio_client = get_minio_client()

        receipt = json.dumps(
            payload,
            indent=2,
        ).encode()

        minio_client.put_object(
            Bucket=MINIO_BUCKET,
            Key=f"receipts/{order_id}.json",
            Body=receipt,
            ContentType="application/json",
        )

    except Exception:
        mark_order_failed(order_id)
        raise

    return payload
