# OpenSearch Centralized Logging Runbook

## Overview

Stage 15 adds centralized logging to the Ecommerce HA Platform.

Architecture:

app1/app2 -> Docker/FastAPI logs + systemd/journald logs -> Fluent Bit -> OpenSearch -> OpenSearch Dashboards / Discover

Logging VM:
- host: logging
- MGMT IP: 10.10.10.80
- OpenSearch: 9200/tcp
- OpenSearch Dashboards: 5601/tcp
- OpenSearch version: 3.8.0
- OpenSearch Dashboards version: 3.8.0

Application nodes:
- app1: 10.10.10.21
- app2: 10.10.10.22
- Fluent Bit: 5.1.2

## OpenSearch

OpenSearch runs as a systemd service on the logging VM.

Configuration:
cluster.name: ecommerce-logs
node.name: logging
network.host: 10.10.10.80
http.port: 9200
discovery.type: single-node

Security plugin is disabled for this lab stage. TLS/authentication are deferred to Stage 16.

JVM heap:
-Xms2g
-Xmx2g

Validation:
curl -s http://10.10.10.80:9200
curl -s http://10.10.10.80:9200/_cluster/health?pretty

Expected cluster health:
status: green
number_of_nodes: 1

## OpenSearch Dashboards

Configuration:
server.name: ecommerce-logs
server.host: 10.10.10.80
server.port: 5601

opensearch.hosts:
  - http://10.10.10.80:9200

The securityDashboards plugin is removed because OpenSearch Security is disabled.

Validation:
curl -s http://10.10.10.80:5601/api/status

Expected:
overall state: green

Windows SSH tunnel:
ssh -N -i $HOME\.ssh\ecommerce-ha-ed25519 -L 5601:10.10.10.80:5601 aa@172.31.250.129

Browser:
http://127.0.0.1:5601

## Fluent Bit

Fluent Bit 5.1.2 is installed on app1 and app2.

State directory:
/var/lib/fluent-bit/

State DB files:
docker.db
systemd.db

## Application / Docker logs

Input:
Path /var/lib/docker/containers/*/*-json.log
Tag ecommerce.app

Added fields:
host
service=ecommerce-api
environment=lab
log_type=application

Destination:
ecommerce-app-YYYY.MM.DD

## System logs

Input:
systemd / journald
Tag ecommerce.system

Added fields:
host
environment=lab
log_type=system

Destination:
ecommerce-system-YYYY.MM.DD

Important fields:
MESSAGE
SYSTEMD_UNIT
SYSLOG_IDENTIFIER
HOSTNAME

## Index templates

Application template:
name: ecommerce-app
pattern: ecommerce-app-*
number_of_shards: 1
number_of_replicas: 0

Mapped fields:
@timestamp: date
host: keyword
service: keyword
environment: keyword
stream: keyword
source_file: keyword
log: text

System template:
name: ecommerce-system
pattern: ecommerce-system-*
number_of_shards: 1
number_of_replicas: 0

Mapped fields:
@timestamp: date
host: keyword
environment: keyword
log_type: keyword
MESSAGE: text
SYSTEMD_UNIT: keyword
SYSLOG_IDENTIFIER: keyword

Replica count is 0 because this lab uses a single-node OpenSearch cluster.

## Validation

List indices:
curl -s 'http://10.10.10.80:9200/_cat/indices/ecommerce-*?v'

Expected:
ecommerce-app-YYYY.MM.DD
ecommerce-system-YYYY.MM.DD

Both indices should be green.

## OpenSearch Dashboards index patterns

Created:
ecommerce-app-*
ecommerce-system-*

Time field:
@timestamp

## Controlled incident

A deliberately invalid checkout request was sent through the HA VIP:

curl -i \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"customer":"","amount":-1}' \
  http://10.20.20.100/checkout

Expected response:
HTTP/1.1 422 Unprocessable Entity

The event was found in Discover with:
log:"422"

Observed:
host=app2
service=ecommerce-api
POST /checkout HTTP/1.1 422 Unprocessable Entity
stream=stdout
environment=lab
log_type=application

Pipeline validated:
Client -> HAProxy VIP -> FastAPI -> Docker stdout -> Fluent Bit -> OpenSearch -> Discover

## System log validation

Discover pattern:
ecommerce-system-*

Filter:
SYSLOG_IDENTIFIER:"systemd"

Systemd events from both app1 and app2 were visible.

## Screenshots

docs/screenshots/opensearch-app-422-incident.jpg
docs/screenshots/opensearch-system-logs.jpg

## Useful commands

Check OpenSearch:
systemctl status opensearch

Check Dashboards:
systemctl status opensearch-dashboards

Check Fluent Bit:
ansible apps -b -m shell -a 'systemctl status fluent-bit --no-pager'

Cluster health:
curl -s http://10.10.10.80:9200/_cluster/health?pretty

Indices:
curl -s 'http://10.10.10.80:9200/_cat/indices/ecommerce-*?v'

Recent Fluent Bit warnings/errors:
ansible apps -b -m shell -a '
journalctl -u fluent-bit --since "10 minutes ago" --no-pager |
grep -Ei "error|warn" || true
' --ask-become-pass

## Result

Stage 15 provides:
- OpenSearch
- OpenSearch Dashboards
- Fluent Bit on app1/app2
- Centralized FastAPI/Docker logs
- Centralized systemd/journald logs
- Daily indices
- Index templates
- Discover search
- 422 incident validation
- Evidence screenshots
