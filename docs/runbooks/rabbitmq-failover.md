# RabbitMQ Quorum Queue Failover Runbook

## Current architecture

- rabbit1 — 10.40.40.51
- rabbit2 — 10.40.40.52
- rabbit3 — 10.40.40.53
- Cluster size: 3
- Vhost: /ecommerce
- Exchange: orders
- Queue: orders
- Queue type: quorum
- Routing key: order.created

## Normal validation

Check cluster:

    rabbitmqctl cluster_status

Check quorum queue:

    rabbitmq-queues quorum_status --vhost /ecommerce orders

Check queued messages:

    rabbitmqctl list_queues -p /ecommerce name type state messages

## Tested failure scenario

Initial Raft state:

    rabbit1 leader
    rabbit2 follower
    rabbit3 follower

Three persistent messages were published to the orders quorum queue.

Then rabbitmq-server was stopped on rabbit1.

Result:

    rabbit1 nodedown
    rabbit3 elected leader
    rabbit2 remained follower

The queue remained:

    state = running
    messages = 3

The cluster continued operating with a 2/3 majority.

## Recovery

rabbit1 was started again and rejoined the cluster.

It rejoined the quorum group as a follower and synchronized with the active leader.

## Safety notes

A three-member quorum queue tolerates one node failure.

If two of the three quorum members are unavailable, the queue loses majority and becomes unavailable for normal operations.

Do not reset a RabbitMQ node containing production data unless the recovery procedure explicitly requires it.
