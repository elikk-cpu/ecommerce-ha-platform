Stage 17 — PostgreSQL Backup, WAL Archiving and PITR

Overview

Stage 17 implements production-like PostgreSQL backup and Point-In-Time Recovery using:

- PostgreSQL 16
- pgBackRest 2.50
- MinIO S3-compatible storage
- TLS with internal Ecommerce Root CA
- AES-256-CBC encrypted pgBackRest repository
- PostgreSQL WAL archiving
- FULL and DIFF backups
- systemd backup automation
- HA-aware primary/standby backup execution
- isolated PITR validation

Topology:

db1 PRIMARY
    |
    | WAL archive-push
    | FULL / DIFF backup
    v
pgBackRest
    |
    | HTTPS + internal CA verification
    v
MinIO S3
ecommerce-pgbackrest

PostgreSQL replication remains:

db1 PRIMARY
    |
    | async streaming replication
    v
db2 STANDBY


Backup repository

Dedicated MinIO bucket:

ecommerce-pgbackrest

Dedicated MinIO user:

pgbackrest

The user is restricted to the backup bucket using a dedicated MinIO policy.

Anonymous access is disabled.

Repository transport:

https://minio.ecom.test:9000

TLS certificate is issued by:

Ecommerce HA Root CA

pgBackRest verifies the internal CA and does not disable TLS certificate validation.

Repository encryption:

aes-256-cbc

Secrets are stored in:

ansible/vars/backup-vault.yml

The file is encrypted with Ansible Vault and ignored by Git.


pgBackRest configuration

Stanza:

ecommerce

PostgreSQL data directory:

/var/lib/postgresql/16/main

Repository type:

S3

Retention:

FULL backups: 2
DIFF backups: 4


WAL archiving

PostgreSQL configuration:

archive_mode = on
archive_command = 'pgbackrest --config=/etc/pgbackrest/pgbackrest.conf --stanza=ecommerce archive-push %p'
archive_timeout = 60s

Configuration is managed through:

/etc/postgresql/16/main/conf.d/20-pgbackrest.conf

Both database nodes have archiving configuration prepared.

db1 currently operates as PRIMARY.

db2 currently operates as STANDBY.

The standby remains ready for future promotion.


WAL archive validation

A WAL switch was forced on the primary using:

SELECT pg_switch_wal();

Successful archive result:

archived_count = 1
failed_count = 0
last_archived_wal = 000000030000000000000008

The archived WAL was restored from MinIO with:

pgbackrest archive-get

SHA256 comparison:

original:
8ff91db8a01c70fbccbb0904548e25e1c332c6a678ae579d608891eb145fe3f7

restored:
8ff91db8a01c70fbccbb0904548e25e1c332c6a678ae579d608891eb145fe3f7

Result:

WAL MATCH: YES

This confirms successful:

PostgreSQL
→ pgBackRest
→ TLS
→ MinIO
→ encrypted repository
→ archive-get
→ identical WAL


FULL backup

Initial FULL backup:

20260915-001822F

Backup completed successfully.

Database size:

29.5MB

Repository backup size:

3.9MB

Backup verification:

status: valid
total files checked: 1268
total valid files: 1268
missing: 0
checksum invalid: 0
size invalid: 0

WAL verification:

total WAL checked: 4
total valid WAL: 4
missing: 0
checksum invalid: 0
size invalid: 0

Result:

RC=0


Automated backups

Backups are scheduled through systemd timers on both database nodes.

FULL backup schedule:

Sunday 02:00 UTC

DIFF backup schedule:

Monday-Saturday 02:30 UTC

Timers:

ecommerce-pgbackrest-full.timer
ecommerce-pgbackrest-diff.timer

Backup service:

ecommerce-pgbackrest-backup@.service

HA-aware wrapper:

/usr/local/sbin/ecommerce-pgbackrest-backup

The wrapper checks PostgreSQL role before starting a backup.

Behavior:

PRIMARY -> START backup
STANDBY -> SKIP

Standby test:

role=STANDBY backup_type=diff action=SKIP
Result=success

Primary test:

role=PRIMARY backup_type=diff action=START
backup command end: completed successfully

DIFF backup created:

20260915-001822F_20260915-002207D

It references:

20260915-001822F


PITR test

A dedicated test table was created:

public.pitr_lab

Application tables were not modified.

Initial state:

id=1
marker=KEEP_BEFORE_TARGET

PITR target:

2026-09-15 00:24:02.816236+00

Changes performed after the target:

id=1 -> CORRUPTED_AFTER_TARGET
id=2 -> CREATED_AFTER_TARGET

A WAL switch was forced after the changes so the required WAL was archived.


PITR restore

The restore was performed into an isolated directory:

/var/lib/postgresql/16/pitr-lab

Production PGDATA remained:

/var/lib/postgresql/16/main

pgBackRest selected backup:

20260915-001822F_20260915-002207D

Recovery target:

2026-09-15 00:24:02.816236+00

Recovery mode:

time

Target action:

promote

The restored cluster used:

port: 55432
Unix socket: /tmp
TCP listener: disabled

Production PostgreSQL remained online during validation.


PITR recovery result

PostgreSQL recovery log confirmed:

recovery stopping before commit of transaction 911,
time 2026-09-15 00:24:07.85974+00

Last completed transaction:

2026-09-15 00:24:02.730611+00

Configured PITR target:

2026-09-15 00:24:02.816236+00

This means PostgreSQL restored the transaction before the target and rejected the later destructive transaction.


Final PITR validation

Production state:

id=1 -> CORRUPTED_AFTER_TARGET
id=2 -> CREATED_AFTER_TARGET

Restored PITR state:

id=1 -> KEEP_BEFORE_TARGET
id=2 -> absent

Automated validation result:

PITR VALIDATION: PASS

After recovery:

PITR INSTANCE: PROMOTED
recovery.signal removed
TCP 55432: NOT LISTENING

The PITR instance was stopped after validation.

Production remained:

active
PRIMARY

Streaming replication to db2 remained operational.


Failure scenarios encountered

Several real failure scenarios were diagnosed during implementation.

pgBackRest 2.50 rejected plain HTTP S3 access:

expected protocol 'https'

MinIO was therefore migrated to HTTPS using the internal PKI.

TLS verification also rejected the MinIO IP endpoint:

ERROR [095]:
unable to find hostname '10.40.40.61'
in certificate common name or subject alternative names

The endpoint was changed to:

minio.ecom.test

which is present in the certificate DNS SAN.

During PITR validation PostgreSQL initially rejected:

max_connections = 20

because the source cluster used:

max_connections = 100

After matching the required recovery parameter, PITR continued successfully.

These failures were resolved without modifying or stopping the production PostgreSQL cluster.


Result

Stage 17 demonstrates:

encrypted off-host backups
continuous WAL archiving
verified FULL backup
verified DIFF backup
backup retention
HA-aware automated scheduling
TLS-protected S3 repository
repository integrity verification
WAL restore verification
Point-In-Time Recovery
isolated restore validation
production-safe PITR testing

Final PITR validation:

PASS

