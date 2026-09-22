# BusinessHub — Operational Runbooks

---

## Deployment

**Preflight:** Ensure PostgreSQL and environment variables are correctly configured.

**Procedure:**
1. Build the backend container: `docker build -t businesshub-backend:latest backend/`
2. Apply database migrations (if required): `alembic upgrade head` (on a single runner, not parallel workers).
3. Restart the application stack: `docker compose up -d`
4. Validate readiness: `curl http://localhost:8000/api/v1/health/ready`
5. Smoke test core endpoints (login, health, authenticated endpoint).

**Rollback:** Revert to previous container tag and restart.

---

## Migration

**Pre-migration Backup:** Always perform a full logical backup before applying migrations.
**Command:** `pg_dump $DATABASE_URL | gzip > backups/pre_migration_$TIMESTAMP.sql.gz`

**Procedure:**
1. Apply Alembic upgrades: `alembic upgrade head`
2. Verify revision: `alembic current`

**Failure handling:** Stop the application and restore from backup if schema becomes inconsistent.

---

## Backup

**Execution:** `./ops/backup.sh`
**Retention:** Configure backup archival/cleanup policy independently based on storage and compliance needs.
**Validation:** Check that the backup file was created, is non-empty, and is readable.

---

## Restore

**Procedure:**
1. Stop write traffic or place the application in maintenance mode.
2. Provision a clean PostgreSQL instance or target database.
3. Restore from backup: `./ops/restore.sh <path_to_backup.sql.gz>`
4. Apply Alembic migrations if the backup is older than the current schema head.
5. Validate schema: `alembic current`
6. Start application and verify readiness.
7. Perform a smoke test of business-critical flows.

---

## Database Outage

**Detection:** Application will return 503 on the `/ready` endpoint.
**Action:** Investigate PostgreSQL instance health. Restart or failover to standby depending on infrastructure.

---

## Application Outage

**Detection:** Health endpoint fails to respond.
**Action:** Restart the application container. Inspect logs (`docker logs backend`). Check readiness and database connectivity.

---

## Secret Rotation

**Procedure:**
1. Update the secret in the Secret Manager / environment configuration.
2. Redeploy or restart the application service to pick up the new secret.
3. Validate that the application boots and authentication works as expected.

---

## TLS/Certificate Renewal

**Procedure:** Ensure the reverse proxy (nginx / load balancer) receives the renewed TLS certificate.
**Validation:** Check HTTPS access and inspect certificate expiration.

---

## Failed Release

**Procedure:**
1. Stop the rollout / redeploy.
2. Investigate application logs and readiness endpoints.
3. Roll back the application to the previous known-good container tag.
4. If a destructive migration was applied, evaluate database restore from backup.
