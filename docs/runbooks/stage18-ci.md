Stage 18 — CI Pipeline, Security Scanning and GHCR

Overview

Stage 18 implements a production-like CI pipeline for the Ecommerce HA Platform application.

Pipeline flow:

git push / pull request
    ↓
Ruff lint
    ↓
Pytest
    ↓
Docker build
    ↓
Trivy CRITICAL vulnerability scan
    ↓
GHCR publish

1. Production regression fixed before CI

After MinIO was migrated from HTTP to HTTPS during Stage 17, the application still used:

MINIO_ENDPOINT=http://10.40.40.61:9000

This caused:

/ready -> minio:false
/checkout -> 503 Checkout dependency failure

The application was updated to use:

MINIO_ENDPOINT=https://minio.ecom.test:9000

The Ecommerce Root CA is mounted inside the application containers and used through:

AWS_CA_BUNDLE=/etc/ecommerce-pki/ecommerce-root-ca.crt

Validation after the fix:

/ready -> ready
postgresql -> true
redis -> true
rabbitmq -> true
minio -> true
/checkout -> HTTP 201
status -> created

2. Python quality checks

Development dependencies were added in:

app/requirements-dev.txt

Tools:

- pytest
- httpx
- ruff

Ruff configuration:

app/ruff.toml

Pytest configuration:

app/pytest.ini

The application source directory was made an explicit Python package with:

app/src/__init__.py

3. Automated tests

Test file:

app/tests/test_api.py

Tests implemented:

- root endpoint
- health endpoint
- ready endpoint with healthy dependencies
- ready endpoint with failed dependency
- successful checkout
- checkout dependency failure

Final result:

6 passed

4. Linting

Ruff checks:

app/src
app/tests

Final result:

All checks passed!

5. GitHub Actions

Workflow:

.github/workflows/ci.yml

Triggers:

- push to main
- pull_request to main

Jobs:

Lint and test
    - checkout repository
    - Python 3.12
    - install dependencies
    - Ruff
    - Pytest

Build, scan and publish
    - Docker build
    - Trivy scan
    - GHCR login
    - image tagging
    - image push

6. Trivy security gate

Policy:

severity: CRITICAL
exit-code: 1
ignore-unfixed: true

The first Trivy-enabled pipeline failed because three CRITICAL vulnerabilities were detected in the Debian base image.

The security gate correctly blocked the pipeline before image publication.

The Dockerfile was updated to install current Debian security updates:

apt-get update
apt-get upgrade -y

After rebuilding, the next pipeline completed successfully.

7. GitHub Container Registry

After linting, tests, Docker build and Trivy scan succeed, the image is published to:

ghcr.io/<repository-owner>/ecommerce-api

Tags:

- latest
- commit SHA

8. Successful CI flow

Final successful pipeline:

Lint and test            PASS
Build, scan and publish  PASS

Validated stages:

Ruff                     PASS
Pytest                   PASS
Docker build             PASS
Trivy CRITICAL scan      PASS
GHCR publish             PASS

9. Negative CI validation

A temporary branch was created:

test/ci-negative

An intentional lint error was added to:

app/tests/test_api.py

Ruff detected:

E402 Module level import not at top of file
F401 imported but unused

A pull request from:

test/ci-negative -> main

was created.

Expected CI result:

Lint and test             FAIL
Build, scan and publish   SKIPPED

The pipeline behaved exactly as expected.

The bad-code branch was not merged.

The pull request was closed and the temporary branch was deleted locally and remotely.

10. Final repository state

branch: main
origin/main: synchronized
working tree: clean

The intentionally broken code is not present in main.

11. Stage 18 result

Stage 18 demonstrates:

- automated Python linting
- automated API/unit tests
- Docker image build
- enforced vulnerability scanning
- real security failure handling
- GHCR image publishing
- pull request CI validation
- negative pipeline validation
- dependency-gated CI jobs
- production regression diagnosis and repair

Final result:

CI pipeline operational and enforced.

