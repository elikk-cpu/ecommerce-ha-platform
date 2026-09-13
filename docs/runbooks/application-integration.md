# Application Integration and HA Runbook

## Application architecture

The FastAPI application runs on:

- app1 — 10.30.30.21
- app2 — 10.30.30.22

Traffic path:

    Client
      |
      v
    VIP 10.20.20.100
      |
      v
    HAProxy
      |
      +---- app1
      |
      +---- app2

The application integrates with:

- PostgreSQL
- Redis Sentinel
- RabbitMQ quorum queues
- MinIO S3 storage

## Health endpoints

Liveness:

    /health

Readiness:

    /ready

Readiness validates:

- PostgreSQL
- Redis
- RabbitMQ
- MinIO

## Checkout flow

    POST /checkout
          |
          +--> PostgreSQL: create order
          |
          +--> Redis: cache order
          |
          +--> RabbitMQ: publish order.created
          |
          +--> MinIO: store receipt

## Tested HA scenarios

### Application node failure

app1 was stopped.

HAProxy removed app1 from rotation and all checkout requests
continued through app2.

After app1 returned, HAProxy automatically restored it.

### Redis failover

Redis Primary failed.

Sentinel reached quorum and promoted the replica.

The application experienced a short HTTP 503 window during election
and recovered automatically without redeployment.

### RabbitMQ failover

The leader of the orders quorum queue was stopped.

A new Raft leader was elected from the remaining nodes.

The quorum queue remained available and checkout continued successfully.

### PostgreSQL failover

Initial topology:

    db2 PRIMARY
    db1 STANDBY

db2 was stopped and fenced.

db1 was manually promoted.

Internal DNS was changed:

    db-primary.ecom.test -> 10.40.40.31

The application reconnected to db1 and checkout recovered.

db2 was rebuilt using pg_basebackup and rejoined as a standby.

Final topology:

    db1 PRIMARY
    db2 STANDBY

Streaming replication was verified.

## Current PostgreSQL endpoint

    db-primary.ecom.test -> 10.40.40.31

## Important limitation

PostgreSQL failover in this project is intentionally manual.

Automatic PostgreSQL leader election such as Patroni is outside
the scope of this project.
