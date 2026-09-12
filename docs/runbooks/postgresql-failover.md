# PostgreSQL Manual Failover Runbook

## Current topology

- Primary: db2 — 10.40.40.32
- Standby: db1 — 10.40.40.31
- Application DB endpoint: db-primary.ecom.test
- Replication: asynchronous streaming replication

## Safety rule

Never promote a standby until the old primary is confirmed stopped or isolated.

Running two writable primaries can cause split-brain and data divergence.

## Health checks

Standby:

    SELECT pg_is_in_recovery();

Expected:

    true

Primary:

    SELECT client_addr, state, sync_state
    FROM pg_stat_replication;

Expected:

    state = streaming

## Failover procedure

1. Confirm failure of the current primary.
2. Stop or fence the old primary.
3. Confirm TCP/5432 on the old primary is unavailable.
4. Promote the standby.
5. Verify `pg_is_in_recovery()` returns `false`.
6. Perform a test write on the new primary.
7. Change `db-primary.ecom.test` to the new primary IP.
8. Verify DNS resolution from application nodes.
9. Rebuild the old primary from the new primary using `pg_basebackup`.
10. Start the rebuilt node as a standby.
11. Verify `pg_is_in_recovery()` returns `true` on the standby.
12. Verify `pg_stat_replication` reports `streaming` on the primary.

## Tested scenario

Initial:

    db1 PRIMARY
        |
        | WAL streaming
        v
    db2 STANDBY

Failover:

    db1 STOPPED
    db2 PROMOTED

Rejoin:

    db2 PRIMARY
        |
        | WAL streaming
        v
    db1 STANDBY

The reverse replication test was successfully validated after rejoining db1.
