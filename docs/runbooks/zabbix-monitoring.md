# Zabbix Monitoring Runbook

## Overview

The Ecommerce HA Platform is monitored by Zabbix 7.0.

Zabbix monitors all 16 virtual machines and provides both infrastructure-level
and service-level visibility.

The monitoring stack validates:

- Linux host availability and system metrics
- FastAPI application readiness
- Keepalived VIP ownership
- PostgreSQL primary/standby topology
- PostgreSQL streaming replication
- Redis master/replica topology
- Redis replication health
- Redis Sentinel quorum
- RabbitMQ node availability
- RabbitMQ cluster health
- RabbitMQ quorum queue health
- MinIO health

## Infrastructure monitoring

All 16 hosts are registered in the Zabbix host group:

Ecommerce HA Platform

The standard template:

Linux by Zabbix agent

is attached to every host.

Zabbix Agent2 listens on TCP/10050.

Normal infrastructure state:

Available:      16
Not available:  0
Mixed:          0
Unknown:        0

## Custom application monitoring

### FastAPI

Custom key:

ecommerce.app.ready

Expected values:

1 = READY
0 = NOT READY

The check queries the FastAPI /ready endpoint.

Hosts:

app1
app2

Trigger:

Ecommerce API <host> is not ready

## Keepalived VIP monitoring

Custom key:

ecommerce.vip.present

Expected values:

1 = VIP PRESENT
0 = VIP ABSENT

The production VIP is:

10.20.20.100

Only one load balancer should own the VIP at a time.

Normal state:

lb1 = PRESENT
lb2 = ABSENT

A trigger detects the condition where the VIP is missing from both load
balancers.

## PostgreSQL HA monitoring

Custom keys:

ecommerce.pg.role
ecommerce.pg.replication

Role mapping:

1 = PRIMARY
0 = STANDBY

Replication mapping:

1 = HEALTHY
0 = UNHEALTHY

Normal topology:

db1 = PRIMARY
db2 = STANDBY

The HA topology trigger allows:

1 / 0
0 / 1

and considers the following invalid:

1 / 1  -> possible split-brain
0 / 0  -> no primary

## Redis HA monitoring

Custom keys:

ecommerce.redis.role
ecommerce.redis.replication
ecommerce.redis.sentinel_quorum

Role mapping:

1 = MASTER
0 = REPLICA

Normal topology:

redis1 = MASTER
redis2 = REPLICA

Sentinel quorum is monitored on:

redis1
redis2
rabbit3

At least two Sentinel instances must report healthy quorum.

## RabbitMQ HA monitoring

Custom keys:

ecommerce.rabbit.node
ecommerce.rabbit.cluster
ecommerce.rabbit.quorum

Expected health value:

1 = HEALTHY
0 = UNHEALTHY

RabbitMQ consists of three nodes:

rabbit1
rabbit2
rabbit3

The orders queue uses RabbitMQ quorum queues.

### Monitoring cache

RabbitMQ CLI commands are relatively expensive on small 1-vCPU lab VMs.

Instead of executing Erlang CLI commands for every Zabbix poll, a systemd
timer periodically updates cached health values:

zabbix-rabbitmq-cache.service
zabbix-rabbitmq-cache.timer

Cache files are stored under:

/var/cache/zabbix-rabbitmq/

Zabbix Agent2 reads these cached values, making checks effectively
instantaneous and avoiding monitoring-induced load.

## MinIO monitoring

Custom key:

ecommerce.minio.ready

Expected values:

1 = HEALTHY
0 = UNHEALTHY

The check uses the MinIO health endpoint.

## Dashboard

Dashboard:

Ecommerce HA Overview

The dashboard displays:

- Active problems
- Infrastructure availability
- Problems by severity
- PostgreSQL role state
- Redis role state
- RabbitMQ cluster health
- RabbitMQ quorum queue health
- Keepalived VIP ownership
- MinIO health
- FastAPI readiness

## Incident validation

A controlled application failure was performed on app2.

### Failure injection

The FastAPI container was stopped:

ansible app2 -b -m shell -a '
docker stop ecommerce-api
' --ask-become-pass

Zabbix then reported:

App2 readiness = NOT READY (0)

and raised the trigger:

Ecommerce API app2 is not ready

The virtual machine itself remained available in Zabbix.

This demonstrates that the monitoring system distinguishes between a host
failure and an application failure.

### HA service continuity

While app2 was unavailable, requests through the HA VIP were tested:

for i in {1..5}; do
  curl -s -o /dev/null -w "request $i -> HTTP %{http_code}\n" \
    http://10.20.20.100/health
  sleep 1
done

Result:

HTTP 200
HTTP 200
HTTP 200
HTTP 200
HTTP 200

HAProxy automatically continued serving traffic through app1.

Therefore:

Application node failure -> detected
Alert -> generated
Client service -> remained available

## Recovery validation

The application container was started again:

ansible app2 -b -m shell -a '
docker start ecommerce-api
' --ask-become-pass

The Zabbix readiness check returned:

app2 readiness = 1

The dashboard returned to:

app1 = READY
app2 = READY

The application problem automatically recovered and disappeared from
Active problems.

## Incident result

The complete lifecycle was successfully validated:

Healthy
   |
   v
Application failure
   |
   v
Zabbix detection
   |
   v
High severity alert
   |
   v
HAProxy maintains service through app1
   |
   v
Application recovery
   |
   v
Zabbix detects recovery
   |
   v
Healthy

This validates detection, alerting, service continuity and recovery
monitoring for an application-node failure.
