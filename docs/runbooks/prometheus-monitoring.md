# Prometheus / Grafana / Alertmanager Monitoring Runbook

## Overview

The Ecommerce HA Platform uses Prometheus, Grafana and Alertmanager for metrics-based observability.

The monitoring stack runs on the monitor VM:

- Prometheus: 9090
- Grafana: 3000
- Alertmanager: 9093
- node_exporter: 9100

## Prometheus targets

Final state:

26 total
26 up
0 down

Targets:

- 16 node_exporter
- 2 FastAPI
- 2 PostgreSQL exporter
- 2 Redis exporter
- 3 RabbitMQ Prometheus
- 1 Prometheus self-monitoring target

## Node Exporter

node_exporter is installed on all 16 VMs and exposes metrics on TCP/9100.

Metrics include CPU, memory, filesystem, network and host availability.

## FastAPI metrics

FastAPI exposes Prometheus metrics at:

/metrics

Production traffic:

10.30.30.21:8000
10.30.30.22:8000

Prometheus monitoring path:

10.10.10.21:9101
10.10.10.22:9101

Application metrics include:

ecommerce_http_requests_total
ecommerce_checkouts_total

## PostgreSQL metrics

Exporter endpoints:

db1:9187
db2:9187

Monitoring role:

prometheus

Role membership:

pg_monitor

Local datasource:

user=prometheus host=/run/postgresql dbname=postgres

Normal topology:

db1 = PRIMARY
db2 = STANDBY

Both exporters report:

pg_up 1

## Redis metrics

Exporter endpoints:

redis1:9121
redis2:9121

Authentication uses the existing Ansible Vault variable:

vault_redis_password

The secret is not committed to Git.

Normal topology:

redis1 = MASTER
redis2 = REPLICA

Both exporters report:

redis_up 1

## RabbitMQ metrics

RabbitMQ uses the built-in plugin:

rabbitmq_prometheus

Metrics port:

15692/tcp

Nodes:

rabbit1
rabbit2
rabbit3

## Grafana

Grafana runs on the monitor VM and uses Prometheus as its default datasource:

http://127.0.0.1:9090

Dashboard:

Ecommerce Observability Overview

Panels:

- Hosts UP
- CPU Usage
- RAM Usage
- Disk Usage
- Network Traffic
- FastAPI Request Rate
- Checkout Rate
- PostgreSQL Connections
- Redis Commands Rate
- RabbitMQ Ready Messages

## Alertmanager

Prometheus sends alerts to:

http://127.0.0.1:9093

Configured rules:

- NodeExporterDown
- FastAPIDown
- PostgreSQLExporterDown
- RedisExporterDown
- RabbitMQMetricsDown

Rules file:

/etc/prometheus/rules/ecommerce-alerts.yml

## Incident validation

A controlled failure was performed on app2.

Failure injection:

ansible app2 -b -m shell -a '
docker stop ecommerce-api
' --ask-become-pass

Prometheus detected:

FastAPIDown
instance=app2
state=firing
severity=critical

Alertmanager received:

FastAPIDown
instance=app2
severity=critical
summary=FastAPI metrics endpoint down on app2

During the incident, the application remained available through the HA VIP because HAProxy continued routing traffic to app1.

## Recovery validation

Recovery:

ansible app2 -b -m shell -a '
docker start ecommerce-api
' --ask-become-pass

Final state:

app2 up=1

Prometheus:
FastAPIDown active alerts = 0

Alertmanager:
FastAPIDown active alerts = 0

## Screenshots

docs/screenshots/grafana-observability-overview.jpg
docs/screenshots/prometheus-alert-firing.jpg
docs/screenshots/prometheus-alert-recovery.jpg

## Operational checks

Prometheus targets:

curl -s http://127.0.0.1:9090/api/v1/targets

Prometheus active alerts:

curl -s http://127.0.0.1:9090/api/v1/alerts

Alertmanager alerts:

curl -s http://127.0.0.1:9093/api/v2/alerts

Validate Prometheus config:

promtool check config /etc/prometheus/prometheus.yml

Validate alert rules:

promtool check rules /etc/prometheus/rules/ecommerce-alerts.yml
