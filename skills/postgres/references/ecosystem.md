# PostgreSQL: ORM Integration and Cloud PostgreSQL

Companion to `postgres/SKILL.md`.

## ORM Integration

### SQLAlchemy (Python)

- Use SQLAlchemy 2.0 style with async support.
- Configure connection pooling: `create_async_engine(url, pool_size=10, max_overflow=20)`.
- Use Alembic for migrations with `--autogenerate`.
- Prevent N+1: Use `selectinload()` or `joinedload()` for eager loading.

### Prisma (TypeScript)

- Schema-first approach with `prisma.schema`.
- Use two connection strings for pooled environments: `DATABASE_URL` (pooled) and `DIRECT_URL` (direct for migrations).
- `prisma migrate deploy` for production, `prisma migrate dev` for development.

### General ORM Rules

- Always set connection pool sizes. Default is often too high.
- Disable implicit `SELECT *` -- select only needed columns.
- Log generated SQL in development to catch N+1 and inefficient queries.
- Use raw SQL for complex queries that ORMs generate poorly.

## Cloud PostgreSQL

### AWS RDS / Aurora PostgreSQL

- Aurora: Up to 5x throughput over standard PostgreSQL. Read replicas share storage.
- Use RDS Performance Insights for query analysis.
- Multi-AZ for HA. Cross-region read replicas for DR.

### Neon (Serverless PostgreSQL)

- Scale to zero, instant branching for dev/preview.
- Built-in connection pooling via PgBouncer (up to 10K connections to pooler).
- Use pooled endpoint for application, direct endpoint for migrations.

### Supabase

- Managed PostgreSQL with built-in auth, RLS, and real-time.
- RLS is the primary access control mechanism.
- Use `(SELECT auth.uid())` pattern in RLS policies for performance.
