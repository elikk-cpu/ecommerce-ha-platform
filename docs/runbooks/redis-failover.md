# Redis Sentinel Failover Runbook

## Current topology

- Primary: redis2 — 10.40.40.42:6379
- Replica: redis1 — 10.40.40.41:6379
- Sentinel nodes:
  - redis1 — 10.40.40.41:26379
  - redis2 — 10.40.40.42:26379
  - rabbit3 — 10.40.40.53:26379
- Sentinel quorum: 2

## Normal checks

Check current master:

    SENTINEL get-master-addr-by-name ecommerce-master

Check quorum:

    SENTINEL ckquorum ecommerce-master

Check Redis role:

    ROLE

## Tested failover

Initial topology:

    redis1 PRIMARY
        |
        v
    redis2 REPLICA

Failure:

    redis1 Redis service stopped

Sentinel result:

    3 Sentinels detected failure
    quorum 2/3 reached
    redis2 automatically promoted

Result:

    redis2 PRIMARY
        |
        v
    redis1 REPLICA

The old primary was restarted and automatically rejoined as a replica.

## Safety notes

- Do not manually force both Redis nodes to master.
- Applications should discover the current primary through Sentinel.
- Sentinel does not automatically fail back to the former primary.
- After failover, update automation variables to reflect the new topology.
