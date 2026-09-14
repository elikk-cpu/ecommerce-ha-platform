# Stage 16 — Security, Internal CA and TLS

## Overview

Stage 16 adds PKI, authentication, authorization, TLS and basic security
hardening to the ecommerce HA platform.

Implemented:

- Internal Root CA
- Service certificates
- OpenSearch Security plugin
- OpenSearch HTTPS and transport TLS
- OpenSearch internal users and RBAC
- Fluent Bit authenticated TLS ingestion
- OpenSearch Dashboards authentication and HTTPS
- HAProxy HTTPS termination on the Keepalived VIP
- HTTP to HTTPS redirect
- TLS protocol hardening
- Security response headers
- Positive and negative security validation

---

## Internal PKI

The internal CA is stored on the bastion host:

```text
/etc/ecommerce-pki/
├── ca/
├── private/
├── issued/
└── csr/
```

Root CA:

```text
CN = Ecommerce HA Root CA
O  = Ecommerce HA Platform
OU = Infrastructure
```

The Root CA private key remains only on the bastion and is never committed
to Git.

Issued certificates include:

- OpenSearch node certificate
- OpenSearch superadmin certificate
- OpenSearch Dashboards HTTPS certificate
- HAProxy VIP HTTPS certificate

---

## OpenSearch Security

OpenSearch Security was enabled on the logging node.

OpenSearch API:

```text
https://10.10.10.80:9200
```

Plain HTTP access is disabled.

Authentication:

- `admin` — administrative user
- `kibanaserver` — OpenSearch Dashboards service account
- `fluentbit` — log shipping service account

Passwords are stored in:

```text
ansible/vars/opensearch-vault.yml
```

The file is encrypted with Ansible Vault and excluded from Git.

The OpenSearch Security index was initialized with `securityadmin.sh`.

Security index:

```text
.opendistro_security
```

The cluster remained GREEN after security initialization.

---

## OpenSearch TLS

TLS is enabled for:

- REST API on port 9200
- OpenSearch transport on port 9300

Allowed TLS versions:

```text
TLSv1.2
TLSv1.3
```

TLS 1.1 and older protocols are rejected.

Anonymous requests to the OpenSearch API return HTTP 401.

---

## Fluent Bit RBAC

Fluent Bit sends application and system logs to OpenSearch using:

```text
HTTPS
CA verification
HTTP Basic authentication
```

User:

```text
fluentbit
```

Role:

```text
fluentbit_writer
```

Allowed indices:

```text
ecommerce-app-*
ecommerce-system-*
```

The Fluent Bit account can write logs but cannot read them.

Negative RBAC validation:

```text
Fluent Bit read request -> HTTP 403
```

Secure ingestion was validated from both application nodes:

```text
app1 -> OpenSearch OK
app2 -> OpenSearch OK
```

---

## OpenSearch Dashboards

OpenSearch Dashboards is protected by the Security plugin.

Endpoint:

```text
https://10.10.10.80:5601
```

Access from the workstation is performed through the bastion SSH tunnel.

The browser trusts the Ecommerce HA Root CA.

Dashboards uses the `kibanaserver` service account to connect to OpenSearch
through HTTPS.

Unauthenticated users are redirected to the login page.

Existing index patterns remained available:

```text
ecommerce-app-*
ecommerce-system-*
```

Allowed TLS versions:

```text
TLSv1.2
TLSv1.3
```

---

## HAProxy HTTPS

External application traffic is exposed through the Keepalived VIP:

```text
10.20.20.100
```

HAProxy listeners:

```text
HTTP  :80
HTTPS :443
```

HTTP traffic is redirected permanently:

```text
HTTP -> 301 -> HTTPS
```

HAProxy terminates TLS and forwards requests to the FastAPI application
nodes over the internal APP network.

Certificate:

```text
CN  = ecommerce.ecom.test
SAN = ecommerce.ecom.test, 10.20.20.100
```

TLS validation confirmed:

```text
TLS 1.2 -> allowed
TLS 1.3 -> allowed
TLS 1.1 -> rejected
```

HAProxy continues to balance requests between app1 and app2.

---

## HAProxy Security Headers

The HTTPS frontend returns:

```text
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
```

---

## Security Validation

The final Ansible validation verified:

- HAProxy active on lb1/lb2
- valid HAProxy configuration
- HTTPS VIP health check returns HTTP 200
- OpenSearch service active
- anonymous OpenSearch request denied
- authenticated OpenSearch API available
- OpenSearch cluster healthy
- temporary superadmin credentials removed
- OpenSearch Dashboards active
- Dashboards login protection active
- Fluent Bit active on app1/app2

All validation tasks completed with:

```text
failed=0
```

---

## Negative Security Tests

The following negative tests were executed successfully:

```text
HTTP application access
    -> 301 redirect to HTTPS

OpenSearch plaintext HTTP
    -> blocked

Anonymous OpenSearch HTTPS
    -> HTTP 401

Incorrect admin password
    -> HTTP 401

Fluent Bit read access
    -> HTTP 403

Anonymous Dashboards request
    -> redirected to authentication
```

This validates authentication, least privilege and transport security.

---

## Security Incident During Deployment

During the first OpenSearch Security cutover, OpenSearch failed to start with:

```text
java.nio.file.AccessDeniedException: /etc/opensearch/admin-tmp
```

Temporary superadmin credentials had been placed inside `/etc/opensearch`
in a root-only directory.

OpenSearch scans its configuration tree during startup and could not access
the directory.

The temporary credentials were moved to:

```text
/run/opensearch-security-admin
```

OpenSearch then started successfully.

After initialization of the Security index, the temporary admin certificate
and private key were removed from the logging host.

The permanent superadmin private key remains only on the bastion.

---

## Secret Management

The following files must never be committed:

```text
ansible/vars/opensearch-vault.yml
*.key
*.pem
```

Validation performed before Git commit:

```bash
git check-ignore -v ansible/vars/opensearch-vault.yml

git ls-files | grep -Ei '\.(key|pem)$|opensearch-vault\.yml$'

git grep -nE 'BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY'
```

No private keys or decrypted Vault secrets are tracked by Git.

---

## Result

Stage 16 security architecture:

```text
Client
  |
  | HTTPS
  v
HAProxy VIP :443
  |
  | HTTP / internal APP network
  v
app1 / app2

Fluent Bit
  |
  | HTTPS + CA verification
  | fluentbit RBAC user
  v
OpenSearch :9200
  |
  | HTTPS + authentication
  v
OpenSearch Dashboards :5601
```

Stage 16 result:

```text
Internal PKI             OK
OpenSearch Security      OK
OpenSearch TLS           OK
Fluent Bit RBAC          OK
Dashboards HTTPS         OK
HAProxy HTTPS            OK
TLS hardening            OK
Security headers         OK
Positive validation      OK
Negative security tests  OK
```

