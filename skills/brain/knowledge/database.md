# Database Best Practices

These guidelines apply to all database skills regardless of specific technology (SQL, NoSQL, cloud-managed, or self-hosted).

---

## 1. Design Principles

### Query-First Modeling

- Identify access patterns **before** designing the schema.
- In NoSQL: design the data model to answer specific queries efficiently.
- In SQL: normalize first (3NF), denormalize only for measured, high-ROI reads.

### Choose the Right Tool

- Relational (PostgreSQL, SQL Server) for complex queries, transactions, ACID.
- Document stores (MongoDB, Cosmos DB) for flexible schemas, horizontal scale.
- Key-value (Redis, DynamoDB) for caching, sessions, high-throughput simple lookups.
- Graph (Neo4j) for relationship-heavy traversal queries.
- Time-series for metrics, IoT, logs.

---

## 2. Security

- **Parameterized queries always**: Never concatenate user input into queries.
- **Least privilege**: Application accounts get only the permissions they need.
- **Encrypt sensitive data**: At rest and in transit.
- **Credential management**: Use managed identity / RBAC / environment variables, never hardcode keys.
- **Audit logging**: Track who accessed or modified sensitive data.

---

## 3. Performance

- **Index for actual query paths**: Don't over-index (write penalty) or under-index (slow reads).
- **Avoid N+1 queries**: Use joins, eager loading, or batch fetching.
- **Use pagination**: Never return unbounded result sets.
- **Monitor query performance**: Use execution plans (EXPLAIN ANALYZE) and query stores.
- **Connection pooling**: Reuse connections; never open/close per request.
- **Cache appropriately**: Cache expensive reads with clear invalidation strategy.

---

## 4. Reliability

- **Backup and test restores**: Untested backups are not backups.
- **Define RTO/RPO**: Know your recovery time and recovery point objectives.
- **Use transactions appropriately**: ACID where needed, eventual consistency where acceptable.
- **Handle transient failures**: Retry with exponential backoff for cloud databases.
- **Monitor health**: Track latency (P50/P95/P99), error rates, connection pool usage, storage.

---

## 5. Operational Discipline

- **Migrations are code**: Version-controlled, reviewable, reversible.
- **Zero-downtime migrations**: Add before remove; backfill, then cut over.
- **Validate configuration at startup**: Connection strings, timeouts, pool sizes.
- **Right-size resources**: Monitor actual usage and adjust (autoscale, reserved capacity).
- **Cost awareness**: Monitor consumption (RU/s, DTU, query cost) and optimize.

---

## 6. Data Integrity

- **Constraints at the database level**: NOT NULL, CHECK, UNIQUE, foreign keys where applicable.
- **Validate at boundaries**: Application validates input, database enforces invariants.
- **Immutability where possible**: Audit trails, temporal tables, soft deletes for critical data.
- **Consistent naming**: snake_case for identifiers, singular table names or match existing convention.
