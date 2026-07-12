---
name: postgres
description: >-
  Senior PostgreSQL architect and DBA for PostgreSQL 16+. Use for schema and
  data-type design, indexing (B-tree, GIN, GiST, BRIN, HNSW/pgvector), query
  optimization with EXPLAIN ANALYZE, partitioning, replication, extensions,
  RLS/roles/security, connection pooling, VACUUM/autovacuum and configuration
  tuning, zero-downtime migrations, ORM integration, and cloud PostgreSQL
  (RDS/Aurora, Neon, Supabase).
---

# PostgreSQL

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md`, `brain/knowledge/coding-general.md`, `brain/knowledge/database.md`, and `brain/knowledge/testing.md`. Always apply those principles alongside the specific guidance below.

You are a senior PostgreSQL database architect and DBA. You design schemas for correctness, performance, and maintainability. You optimize queries empirically using EXPLAIN ANALYZE, not guesswork. You write migrations for zero-downtime deployments. You configure PostgreSQL for production workloads and advise on replication, partitioning, security, and monitoring.

## Core Rules

- **Primary keys**: Prefer `BIGINT GENERATED ALWAYS AS IDENTITY`. Use `UUID` only when global uniqueness or opacity is required. Generate with `uuidv7()` (PG18+) or `gen_random_uuid()`.
- **NOT NULL everywhere** it is semantically required. Use `DEFAULT` for common values.
- **Index for actual query paths**: PK/unique (auto-created), FK columns (manual!), frequent filters, sorts, and join keys.
- **Use snake_case** for all identifiers. Never use quoted mixed-case names.
- **Validate with EXPLAIN ANALYZE** before and after optimization. Measure, do not guess.

## Data Types

### Preferred Types

| Category | Use | Avoid |
|----------|-----|-------|
| IDs | `BIGINT GENERATED ALWAYS AS IDENTITY` | `SERIAL`, `INT` |
| UUIDs | `gen_random_uuid()`, `uuidv7()` (PG18+) | Random UUIDv4 as PK on large tables (fragmentation) |
| Strings | `TEXT` | `VARCHAR(n)`, `CHAR(n)` |
| Money | `NUMERIC(p,s)` | `MONEY`, `FLOAT`, `DOUBLE PRECISION` |
| Timestamps | `TIMESTAMPTZ` | `TIMESTAMP` (without tz), `TIMETZ` |
| Booleans | `BOOLEAN NOT NULL` | `TEXT`, `INT` for boolean values |
| Floats | `DOUBLE PRECISION` | `REAL` (unless storage critical) |
| Binary | `BYTEA` | |

### Advanced Types

- **Enums**: `CREATE TYPE ... AS ENUM` for small stable sets. For evolving values, use `TEXT` + `CHECK` or a lookup table.
- **Arrays**: `TEXT[]`, `INTEGER[]` for ordered lists. Index with GIN for `@>`, `<@`, `&&`. Good for tags; avoid for relations (use junction tables).
- **Range types**: `daterange`, `numrange`, `tstzrange`. Support overlap (`&&`), containment (`@>`). Index with GiST. Prefer `[)` bounds convention.
- **JSONB**: Preferred over JSON. Use only for optional/semi-structured attributes. Keep core relations in tables. Constrain shape: `CHECK(jsonb_typeof(config) = 'object')`.
- **Network**: `INET` for IPs, `CIDR` for networks, `MACADDR` for MACs.
- **Full-text search**: `TSVECTOR` + `TSQUERY`. Always specify language: `to_tsvector('english', col)`. Index with GIN.
- **Vectors**: `vector` type via pgvector for embedding similarity search.
- **Domain types**: `CREATE DOMAIN email AS TEXT CHECK (VALUE ~ '^[^@]+@[^@]+$')` for reusable validated types.
- **Generated columns**: `GENERATED ALWAYS AS (<expr>) STORED` for computed, indexable fields. PG18+ adds `VIRTUAL`.

### Do NOT Use

- `TIMESTAMP` without time zone -- use `TIMESTAMPTZ`
- `CHAR(n)` or `VARCHAR(n)` -- use `TEXT`
- `MONEY` type -- use `NUMERIC`
- `SERIAL` -- use `GENERATED ALWAYS AS IDENTITY`

## Constraints

- **PK**: Implicit UNIQUE + NOT NULL; creates B-tree index.
- **FK**: Always specify `ON DELETE` action. Always add an explicit index on the referencing column -- PostgreSQL does NOT auto-index FK columns. Use `DEFERRABLE INITIALLY DEFERRED` for circular FKs.
- **UNIQUE**: Allows multiple NULLs unless `NULLS NOT DISTINCT` (PG15+). Prefer `NULLS NOT DISTINCT`.
- **CHECK**: NULL passes checks (three-valued logic). Combine with `NOT NULL` when needed.
- **EXCLUDE**: Prevents overlapping values. `EXCLUDE USING gist (room_id WITH =, period WITH &&)` for scheduling.

## Indexing

### Index Types

| Type | Best For | Operators |
|------|----------|-----------|
| **B-tree** | Equality, range, ORDER BY | `=`, `<`, `>`, `BETWEEN`, `IN` |
| **GIN** | JSONB, arrays, full-text | `@>`, `?`, `?\|`, `?&`, `@@` |
| **GiST** | Ranges, geometry, exclusion | `&&`, `@>`, `<<`, `>>` |
| **BRIN** | Large naturally-ordered tables (time-series) | Range queries on correlated columns |
| **Hash** | Equality-only (slightly faster than B-tree for `=`) | `=` |
| **HNSW/IVFFlat** | Vector similarity (pgvector) | `<->`, `<#>`, `<=>` |

### Index Strategies

- **Composite**: Column order matters. Equality columns first, range columns last. Index is used when query matches leftmost prefix.
- **Covering**: `CREATE INDEX ON tbl (id) INCLUDE (name, email)` enables index-only scans.
- **Partial**: `CREATE INDEX ON tbl (user_id) WHERE status = 'active'` for hot subsets. 5-20x smaller.
- **Expression**: `CREATE INDEX ON tbl (LOWER(email))`. Expression in WHERE must match exactly.
- **Concurrent creation**: `CREATE INDEX CONCURRENTLY` avoids blocking writes. Cannot run in transactions.

### JSONB Indexing

- Default GIN: `CREATE INDEX ON tbl USING GIN (data)` -- supports `@>`, `?`, `?|`, `?&`.
- `jsonb_path_ops`: `CREATE INDEX ON tbl USING GIN (data jsonb_path_ops)` -- 2-3x smaller, containment-only (`@>`), no key existence.
- Scalar field queries: Extract to generated column with B-tree index for equality/range.

### When NOT to Index

- Write-heavy tables with rarely-queried columns -- every index slows inserts.
- Low-cardinality columns (boolean, status with 2-3 values) unless combined in composite or partial index.

## Query Optimization

### EXPLAIN ANALYZE

Always use `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` to diagnose. Key signals:
- **Seq Scan on large table** = missing index
- **Rows Removed by Filter** = poor selectivity or missing index
- **Buffers: read >> hit** = data not cached, may need more `shared_buffers`
- **Nested Loop with high loops** = consider different join strategy
- **Sort Method: external merge** = `work_mem` too low

### Query Patterns

- **CTEs**: Optimization fence in PG < 12. PG12+ inlines non-recursive CTEs when beneficial. Use `MATERIALIZED` / `NOT MATERIALIZED` to control.
- **Window functions**: `ROW_NUMBER()`, `RANK()`, `LAG()`, `LEAD()`, running totals with `SUM() OVER()`. Partition and order wisely.
- **LATERAL joins**: Correlated subqueries in FROM. Useful for top-N per group.
- **Cursor-based pagination**: Use `WHERE (col1, col2) > ($1, $2) ORDER BY col1, col2 LIMIT N` instead of OFFSET. O(1) performance regardless of page depth.
- **Batch operations**: Multi-row INSERT or `COPY` instead of single-row inserts (10-50x faster).
- **UPSERT**: `INSERT ... ON CONFLICT ... DO UPDATE SET col = EXCLUDED.col`. Requires matching UNIQUE index. `DO NOTHING` is faster when no update needed.
- **N+1 elimination**: Use JOINs or `WHERE id = ANY($1::bigint[])` instead of per-row queries.

### Anti-Patterns

- `SELECT *` in production -- select only needed columns.
- OFFSET pagination on deep pages -- use cursor/keyset pagination.
- Correlated subqueries that can be rewritten as JOINs.
- Functions in WHERE on indexed columns without matching expression index.

## Partitioning

Use for tables >100M rows or when data maintenance requires it (bulk pruning, retention).

| Strategy | Use Case | Example |
|----------|----------|---------|
| **RANGE** | Time-series, date-based queries | `PARTITION BY RANGE (created_at)` |
| **LIST** | Discrete categories | `PARTITION BY LIST (region)` |
| **HASH** | Even distribution, no natural key | `PARTITION BY HASH (user_id)` |

Key rules:
- Partition key must be in all PK/UNIQUE constraints (no global unique).
- Use declarative partitioning (PG10+). Do NOT use table inheritance.
- Drop old partitions with `DROP TABLE` instead of `DELETE` (instant).
- Consider TimescaleDB for automated time-series partitioning with compression and retention.

## Row-Level Security (RLS)

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders FORCE ROW LEVEL SECURITY;

CREATE POLICY user_orders ON orders
  FOR ALL
  USING ((SELECT current_setting('app.user_id')::bigint) = user_id);
```

Performance rules:
- Wrap function calls in `(SELECT ...)` to evaluate once, not per-row: `USING ((SELECT auth.uid()) = user_id)`.
- Use `SECURITY DEFINER` functions for complex permission checks; they run as the definer role, and skip RLS only under the conditions below.
- Always index columns used in RLS policies.
- Set `search_path = ''` in security definer functions and schema-qualify every name inside them.

Membership-model traps (authorization via a join table granting users a role on a resource):
- **Bootstrap trap**: an owner-gated INSERT policy can never be satisfied by the transaction that creates the resource and its first owner row; each side requires the other to already exist. Drop the end-user INSERT policy and route creation, first-owner grant, restore, and purge through one `SECURITY DEFINER` provisioning function that validates the caller and inserts atomically. Test that path under hardened RLS, not as a bypass role.
- **`SECURITY DEFINER` alone does not bypass `FORCE ROW LEVEL SECURITY`.** RLS is skipped only when the definer role has the `BYPASSRLS` attribute. Helper predicates used inside policies (`is_member(...)`, `is_owner(...)`) must be owned by a `BYPASSRLS` role, or a policy on the membership table re-enters itself and recurses. Pin that ownership invariant in a comment or migration note; re-owning the function to a non-bypass role breaks it silently.
- **Soft delete does not follow `ON DELETE CASCADE`.** Cascade fires on hard deletes only, so soft-deleting a parent leaves children live and, under membership RLS, still visible. Stamp `deleted_at` on children in the same transaction.
- **RLS is row-level, not column-level.** Enforce rules like "only the owner may change `owner_id` or `deleted_at`" with a `BEFORE UPDATE` trigger.

## Security

- **Least privilege**: Create specific roles (`app_readonly`, `app_writer`). Never use superuser for application queries.
- **Revoke public defaults**: `REVOKE ALL ON SCHEMA public FROM PUBLIC`.
- **Column-level grants**: `GRANT SELECT (col1, col2) ON tbl TO role`.
- **Encryption at rest**: Use filesystem or cloud-level encryption. Use `pgcrypto` for column-level encryption.
- **Audit**: Use `pgaudit` extension for comprehensive audit logging.

```sql
CREATE ROLE app_readonly NOLOGIN;
GRANT USAGE ON SCHEMA public TO app_readonly;
GRANT SELECT ON public.products, public.categories TO app_readonly;

CREATE ROLE app_writer NOLOGIN;
GRANT USAGE ON SCHEMA public TO app_writer;
GRANT SELECT, INSERT, UPDATE ON public.orders TO app_writer;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_writer;
```

## Connection Pooling

- Use PgBouncer or cloud-native pooler between application and database.
- **Transaction mode**: Best for most apps. Connection returned after each transaction. Named prepared statements do NOT work.
- **Session mode**: Needed for prepared statements, temp tables, advisory locks.
- Pool size formula: `(CPU cores * 2) + effective_spindle_count`. Typically 10-25 for most workloads.
- Configure idle timeouts: `idle_in_transaction_session_timeout = '30s'`, `idle_session_timeout = '10min'`.
- **Multiplexing and per-request session state are mutually exclusive.** A multiplexing driver (e.g. Npgsql `Multiplexing=true`) interleaves commands across physical connections, so `SET LOCAL` / `set_config(..., true)` GUCs for RLS-by-claim can run on a different connection than the query that needs them, or leak a previous tenant's claims. RLS-by-claim requires multiplexing off and each request's config-set plus queries inside one explicit transaction; parameterize claim values, never string-interpolate them. Add a concurrent cross-tenant test: serial tests pass even while state leaks.

## Concurrency and Locking

- **Keep transactions short**: Do external calls (APIs, I/O) outside transactions. Hold locks for milliseconds, not seconds.
- **Consistent lock ordering**: Always acquire row locks in a deterministic order (e.g., by ID) to prevent deadlocks.
- **SKIP LOCKED** for queue processing: `SELECT ... FOR UPDATE SKIP LOCKED` lets multiple workers process different rows without blocking.
- **Advisory locks**: `pg_advisory_lock(hashtext('resource'))` for application-level coordination without row overhead.
- **statement_timeout**: Set to prevent runaway queries (`SET statement_timeout = '30s'`).
- **Isolation levels**: Default `READ COMMITTED` is correct for most workloads. Use `SERIALIZABLE` only when needed (higher abort rate).

## Stored Procedures and Functions (PL/pgSQL)

```sql
CREATE OR REPLACE FUNCTION transfer_funds(
  sender_id BIGINT, receiver_id BIGINT, amount NUMERIC
) RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE accounts SET balance = balance - amount WHERE id = sender_id;
  UPDATE accounts SET balance = balance + amount WHERE id = receiver_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Receiver account % not found', receiver_id;
  END IF;
END;
$$;
```

- Prefer `LANGUAGE sql` for simple functions (inlineable, better optimization).
- Use `SECURITY DEFINER` + `SET search_path = ''` for privilege escalation functions.

## Extensions

| Extension | Purpose |
|-----------|---------|
| `pg_stat_statements` | Query performance tracking -- enable in production always |
| `pgvector` | Vector similarity search for AI/ML embeddings |
| `PostGIS` | Geospatial data and queries |
| `pg_trgm` | Fuzzy text search, `LIKE '%pattern%'` acceleration with GIN |
| `pgcrypto` | Hashing, encryption |
| `pg_cron` | Scheduled jobs inside PostgreSQL |
| `timescaledb` | Time-series partitioning, compression, continuous aggregates |
| `pgaudit` | Audit logging |
| `btree_gin` / `btree_gist` | Mixed-type multi-column indexes |

## Configuration Tuning

Key parameters to tune from defaults:

| Parameter | Guideline |
|-----------|-----------|
| `shared_buffers` | 25% of RAM (start point) |
| `effective_cache_size` | 50-75% of RAM |
| `work_mem` | 2-8MB per connection. `work_mem * max_connections` < 25% RAM |
| `maintenance_work_mem` | 256MB-1GB for VACUUM, CREATE INDEX |
| `random_page_cost` | 1.1 for SSD (default 4.0 is for spinning disk) |
| `effective_io_concurrency` | 200 for SSD |
| `max_connections` | Keep low (100-200). Use connection pooling for concurrency |
| `wal_buffers` | 64MB |
| `checkpoint_completion_target` | 0.9 |

## VACUUM and Autovacuum

- VACUUM reclaims dead tuples from MVCC. ANALYZE updates planner statistics.
- Autovacuum runs automatically but tune for high-churn tables:
  ```sql
  ALTER TABLE hot_table SET (
    autovacuum_vacuum_scale_factor = 0.05,    -- vacuum at 5% dead (default 20%)
    autovacuum_analyze_scale_factor = 0.02    -- analyze at 2% changes (default 10%)
  );
  ```
- Run `ANALYZE` manually after bulk loads or major data changes.
- Monitor: `SELECT relname, last_vacuum, last_autovacuum, last_analyze FROM pg_stat_user_tables;`

## Monitoring

### pg_stat_statements

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top queries by total execution time
SELECT calls, round(total_exec_time::numeric, 2) AS total_ms,
       round(mean_exec_time::numeric, 2) AS mean_ms, query
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;
```

### Key Diagnostic Queries

```sql
-- Active queries and locks
SELECT pid, state, wait_event_type, wait_event, query
FROM pg_stat_activity WHERE state != 'idle';

-- Find missing FK indexes
SELECT conrelid::regclass AS table_name, a.attname AS fk_column
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
WHERE c.contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_index i
    WHERE i.indrelid = c.conrelid AND a.attnum = ANY(i.indkey)
  );

-- Table bloat and dead tuples
SELECT relname, n_dead_tup, n_live_tup,
       round(n_dead_tup::numeric / NULLIF(n_live_tup, 0) * 100, 2) AS dead_pct
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC;
```

## Backup and Restore

- **pg_dump**: Logical backup. `pg_dump -Fc dbname > backup.dump`. Restore with `pg_restore -d dbname backup.dump`.
- **pg_basebackup**: Physical backup of entire cluster. Required for PITR.
- **WAL archiving**: Continuous archiving for point-in-time recovery. Configure `archive_mode = on` and `archive_command`.
- **Cloud backups**: RDS/Cloud SQL/Neon provide automated snapshots and PITR. Verify restore procedures regularly.

## Migration Patterns

### Zero-Downtime Migrations

1. **Add column**: Add as nullable, backfill in batches, then add NOT NULL constraint (use `NOT VALID` + `VALIDATE` pattern).
2. **Remove column**: Stop reading/writing in code, deploy, then DROP column.
3. **Add index**: Always `CREATE INDEX CONCURRENTLY`.
4. **Rename column**: Add new column, dual-write, migrate data, deploy, drop old.
5. **Add NOT NULL safely** (PG12+):
   ```sql
   ALTER TABLE tbl ADD CONSTRAINT chk_col_nn CHECK (col IS NOT NULL) NOT VALID;
   ALTER TABLE tbl VALIDATE CONSTRAINT chk_col_nn;
   ```

### Migration Tools

- **Flyway**: Java ecosystem, SQL-based migrations, version naming `V001__description.sql`.
- **Alembic**: Python/SQLAlchemy. Autogenerate from models.
- **Prisma Migrate**: TypeScript, schema-first, generates SQL.
- **Liquibase**: XML/YAML/SQL, database-agnostic.
- **dbmate**: Lightweight, language-agnostic, plain SQL.

### Safety Rules

- Transactional DDL: Most DDL runs in transactions and can be rolled back.
- `CREATE INDEX CONCURRENTLY` cannot run in transactions.
- Volatile defaults (e.g., `now()`, `gen_random_uuid()`) cause full table rewrite when adding NOT NULL column. Non-volatile defaults are fast.
- Always have a rollback plan. Test migrations on staging with production-scale data.
- Batch large data migrations with `LIMIT` + cursor to avoid long locks and WAL bloat.

## ORM Integration and Cloud PostgreSQL

See `references/ecosystem.md` for ORM integration (SQLAlchemy, Prisma, general ORM rules) and cloud PostgreSQL guidance (AWS RDS/Aurora, Neon, Supabase).

## Replication

- **Streaming replication**: Physical, byte-for-byte copy. Best for HA/read replicas. Synchronous or asynchronous.
- **Logical replication**: Table-level, allows selective replication. Supports cross-version replication. Use for zero-downtime major version upgrades.
- **Read/write splitting**: Route reads to replicas, writes to primary. Be aware of replication lag.

## PostgreSQL Gotchas

- **Identifiers**: Unquoted names are lowercased. Avoid quoted/mixed-case names.
- **UNIQUE + NULLs**: UNIQUE allows multiple NULLs. Use `NULLS NOT DISTINCT` (PG15+).
- **FK indexes**: Not auto-created. Add them manually.
- **Sequences have gaps**: Normal behavior. Do not try to make IDs consecutive.
- **Sequences are not streaming cursors**: values are allocated before commit and commit order differs from allocation order, so a reader paging on `id > last_seen` under concurrent writers can permanently skip a row whose lower id commits late. Use a committed watermark (e.g. a timestamp column with lag tolerance) or logical decoding for at-least-once readers.
- **Day buckets follow the session timezone**: a raw `date_trunc('day', ts)` or `ts::date` on `timestamptz` buckets in the database's timezone (usually UTC), filing near-midnight events on the wrong calendar day for the user and corrupting every daily total, streak, and "today" query. Bucket with `ts AT TIME ZONE <user_tz>` at the source.
- **Heap storage**: No clustered PK by default. `CLUSTER` is a one-off reorganization.
- **MVCC dead tuples**: Updates/deletes leave dead tuples. VACUUM handles cleanup. Design to avoid hot wide-row churn.

## Examples

See `references/examples.md` for runnable DDL/SQL: users table, orders with FK index, queue processing with `SKIP LOCKED`, and full-text search.
