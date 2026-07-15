![Oracle Analytics Bootcamp](https://zigavaupot.github.io/blogger/paf-deadlock-fix/images/ai-db-paf.png)

I recently deployed **Oracle AI Database Private Agent Factory (OPAF) v26.4.0** on OCI as part of my internal demo and prototyping environment. The goal was straightforward: stand up a Knowledge Agent that could ingest documents and answer questions using OCI GenAI. What I got instead was a frustrating series of database deadlocks that took most of a day to fully resolve. Here's the full story — including every dead end — so you don't have to repeat it.

## The Setup

OPAF runs as a Podman container on an OCI compute VM (`VM.Standard`) in the Frankfurt region. My initial database choice was an **Autonomous Database 26ai Free tier** instance — seemed reasonable for a demo environment. The configuration looks like this:

| Component | Details |
|---|---|
| OPAF version | 26.4.0.0.0 |
| Container | oracle-applied-ai-label (Podman) |
| VM | agentfactoryvm3, OCI Frankfurt |
| Database (initial) | AutonomousDB23ai — ADB 26ai, Free tier |
| LLM | OCI GenAI, meta.llama-3.3-70b-instruct, eu-frankfurt-1 |
| Embedding | Local multilingual-e5-base |

## The Problem

Every single ingestion attempt — whether from a web source, a filesystem PDF, or a URL crawl — failed during the `STORING_CONTENT` stage with this error:

```
AAIKA-00003: Data source 'X' ingestion encountered the following database error
during ingestion stage 'STORING_CONTENT'.
ORA-12801: error signaled in parallel query server P03K, instance 2
ORA-12860: deadlock detected while waiting for a sibling row lock
```

`ORA-12860` is a parallel query deadlock — two parallel query server processes competing for the same row lock. The "instance 2" or "instance 4" in the error was the first real clue.

Running two ingestion jobs simultaneously made it worse (both would fail), but even a single job failed consistently on larger documents.

## Root Cause: ADB Auto-Parallelism

Autonomous Database automatically applies parallelism to queries and DML based on `parallel_degree_policy = AUTO`. On ADB, this policy operates across a **multi-instance (RAC-like) architecture** — even on Free and Developer tier instances. During OPAF's `STORING_CONTENT` stage, it writes document chunks into the knowledge store tables. ADB spins up parallel query servers across instances, and when those servers try to lock the same rows simultaneously, deadlock.

The critical constraint: **you cannot run `ALTER SYSTEM` on ADB**. There's no way to globally disable auto-parallelism as a non-ADMIN system-level change.

## What I Tried (The Long Way)

### Attempt 1: Migrate to Developer Tier

My first hypothesis was that the Free tier was too constrained. I migrated OPAF to point at **ADW-23ai-Dev** (Developer tier, also ADB 26ai). This involved:

1. Downloading the new wallet and placing it in the container mount path
2. Editing `source_env.sh` to update `TNS_ALIAS`, `DB_WALLET`, and `TNS_ADMIN`
3. Fixing `sqlnet.ora` — the downloaded wallet had `DIRECTORY="?/network/admin"` (a placeholder) instead of the actual path
4. Creating the required DB users (`DB26AIPAF` and `AAI_RO_DB26AIPAF`) with the right grants
5. Running the OPAF DB migration manually inside the container

The migration step deserves its own section because it's non-obvious.

### Manual DB Migration

The OPAF container has a `migrate_db.sh` script, but it reads environment variables — not the `applied_ai.properties` file. And the `db_migrate.py` it calls has a toggle system (`setup_toggle.py`) that skips all DDL unless `INSTALL_MODE` and `SETUP_MODE` are set. I had to pass a full set of environment variables:

```bash
podman exec \
  -e DB_USER=DB26AIPAF \
  -e DB_PASSWORD=<password> \
  -e TNS_ALIAS=adw23aid_medium \
  -e TNS_ADMIN=/mount/data/app/latest/datasources/wallets/adw23aid \
  -e DB_WALLET=/mount/data/app/latest/datasources/wallets/adw23aid \
  -e DB_PROTOCOL=tcps \
  -e DB_CONNECTION_TYPE=Wallet \
  -e STRICT_WALLET_MODE=Y \
  -e AGENT_FACTORY_BASE=/home/aaiuser/install/agent_factory \
  -e DB_PATCH_BASE=/home/aaiuser/install/db_patches \
  -e DB_PORT= -e DB_HOST= -e DB_SERVICE= \
  -e INSTALL_MODE=applied_ai \
  -e SETUP_MODE=prod \
  oracle-applied-ai-label \
  /home/aaiuser/install/agent_factory/third_party/python3/bin/python \
  /home/aaiuser/install/agent_factory/common/db_util/db_migrate.py
```

A few gotchas along the way:

- **`sqlnet.ora` placeholder**: The ADB wallet's `sqlnet.ora` uses `"?/network/admin"` which SQLPlus resolves to `$ORACLE_HOME`. You must replace `?` with the actual absolute wallet path.
- **`DB_PORT` conflicts with wallet mode**: If `DB_PORT` is set (even empty-ish), the Oracle connection factory throws `ValueError: Wallet connections only accept TNS_ALIAS and wallet_dir/DB_WALLET. Remove fallback field(s): DB_PORT`. Pass `-e DB_PORT=` explicitly to clear it.
- **Toggle system**: Without `INSTALL_MODE=applied_ai` and `SETUP_MODE=prod`, all DDL steps are skipped silently. The script exits with no output and no error.
- **Note on V$PARAMETER**: When granting privileges, use `GRANT SELECT ON V$PARAMETER TO DB26AIPAF` — not `V_$PARAMETER` (with underscore). The underscore form doesn't exist on ADB.

After migration, 92 tables were created successfully. But the `ORA-12860` deadlock came back immediately on the first ingestion attempt — Developer tier has the same underlying architecture as Free tier.

### Attempt 2: Table-Level NOPARALLEL

```sql
BEGIN
  FOR t IN (SELECT table_name FROM all_tables WHERE owner = 'DB26AIPAF')
  LOOP
    EXECUTE IMMEDIATE 'ALTER TABLE DB26AIPAF.' || t.table_name || ' NOPARALLEL';
  END LOOP;
END;
/
```

No effect. ADB overrides table-level parallelism settings with its AUTO policy.

### Attempt 3: Logon Trigger

Since `ALTER SYSTEM` is unavailable, I tried a logon trigger to disable parallelism at the session level:

```sql
CREATE OR REPLACE TRIGGER DB26AIPAF.disable_parallel
AFTER LOGON ON DB26AIPAF.SCHEMA
BEGIN
  EXECUTE IMMEDIATE 'ALTER SESSION DISABLE PARALLEL QUERY';
  EXECUTE IMMEDIATE 'ALTER SESSION DISABLE PARALLEL DML';
  EXECUTE IMMEDIATE 'ALTER SESSION DISABLE PARALLEL DDL';
  EXECUTE IMMEDIATE 'ALTER SESSION SET parallel_degree_policy = MANUAL';
  EXECUTE IMMEDIATE 'ALTER SESSION SET parallel_max_servers = 0';
END;
/
```

This fires on login — but OPAF uses **connection pooling**. Pooled connections reuse existing sessions and bypass the logon trigger entirely. Still failing.

## What Actually Fixed It: Paid ADB + Restart

Upgrading ADW-23ai-Dev to **full paid service** via OCI Console finally resolved the deadlock. On a paid ADB instance you get dedicated compute, and the auto-parallelism behaviour changes enough that the `NOPARALLEL` table settings and logon trigger together do suppress the deadlocks.

One additional fix that was critical: **restarting the container after repeated ingestion failures**. The OPAF ingestion engine can get stuck in an error state after multiple consecutive failures. A `podman restart oracle-applied-ai-label` clears it.

## The Setup Wizard Gotcha

One thing worth documenting for anyone redoing this: the OPAF setup wizard (at `/agentFactory/installation`) blocks reinstallation if it detects existing schema objects. If you've already run a manual migration, you'll see:

> *Database is not clean for installation. Residual database objects from a previous installation were found.*

And the **Next** button will be greyed out. The fix is to drop and recreate the user before running the wizard:

```sql
DROP USER DB26AIPAF CASCADE;
DROP USER AAI_RO_DB26AIPAF CASCADE;
-- Then recreate with all required grants
```

Also: answer **No** to "Is your database server deployed in an air-gapped environment?" and **Yes** to "Are the OCI certificates added to the wallet?" — otherwise the Knowledge Assistant component won't be installed.

## Complete Grant List for DB26AIPAF

```sql
CREATE USER DB26AIPAF IDENTIFIED BY "<password>";
GRANT DWRole TO DB26AIPAF;
GRANT UNLIMITED TABLESPACE TO DB26AIPAF;
GRANT READ, WRITE ON DIRECTORY DATA_PUMP_DIR TO DB26AIPAF;
GRANT SELECT ON V$PARAMETER TO DB26AIPAF;

CREATE USER AAI_RO_DB26AIPAF IDENTIFIED BY "<password>";
GRANT CREATE SESSION TO AAI_RO_DB26AIPAF;
GRANT SELECT ANY TABLE TO AAI_RO_DB26AIPAF;
```

## Key Takeaways

**Don't use ADB Free or Developer tier for OPAF.** The multi-instance auto-parallelism architecture makes `ORA-12860` deadlocks essentially unavoidable during `STORING_CONTENT`. You need a paid ADB instance where you can actually control parallelism behaviour.

**Don't run concurrent ingestion jobs.** Even on a paid instance, triggering two ingestion jobs simultaneously can reproduce the deadlock. Ingest sources sequentially.

**Restart the container when the ingestion engine gets stuck.** After repeated failures, `podman restart oracle-applied-ai-label` is the fastest recovery path.

**The manual migration is possible but requires the right environment variables.** If you need to migrate OPAF to a different database without going through the UI wizard, the `db_migrate.py` script works — but you need to pass `INSTALL_MODE`, `SETUP_MODE`, and clear `DB_PORT`/`DB_HOST`/`DB_SERVICE` explicitly.

## Useful Commands

```bash
# Check container status
podman ps

# Restart OPAF
podman restart oracle-applied-ai-label

# Follow logs
podman logs -f oracle-applied-ai-label

# Check application log
podman exec oracle-applied-ai-label tail -50 /mount/log/app/latest/log/agent_factory.log

# Check migration log
podman exec oracle-applied-ai-label tail -50 /mount/log/app/latest/log/db_migrate.log
```

---

*Have questions or hit a different variant of this issue? Feel free to reach out — Žiga Vaupot, SmartQ d.o.o.*
