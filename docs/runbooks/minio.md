# MinIO Object Storage Runbook

## Architecture

- Host: minio
- MGMT IP: 10.10.10.61
- DATA IP: 10.40.40.61
- S3 API: 10.40.40.61:9000
- Console: 10.10.10.61:9001
- Persistent data: /srv/minio/data
- Bucket: ecommerce

## Health check

    curl http://10.40.40.61:9000/minio/health/live

Expected HTTP status:

    200

## Container status

    docker ps --filter name=minio

## Logs

    docker logs --tail 100 minio

## Persistence

MinIO data is stored outside the container:

    /srv/minio/data

The bucket and objects survive container restarts.

## Tested scenario

1. Created the ecommerce bucket.
2. Uploaded minio-test.txt.
3. Downloaded and validated the object.
4. Restarted the MinIO container.
5. Verified the health endpoint returned HTTP 200.
6. Repeated the S3 upload/download test successfully.

## Limitation

This lab uses a single MinIO instance.

MinIO itself is therefore a single point of failure.
A production deployment would use distributed MinIO across multiple nodes and disks.
