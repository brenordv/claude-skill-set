# PostgreSQL: Examples

Companion to `postgres/SKILL.md`.

## Users Table

```sql
CREATE TABLE users (
  user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email TEXT NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ON users (LOWER(email));
CREATE INDEX ON users (created_at);
```

## Orders with FK Index

```sql
CREATE TABLE orders (
  order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(user_id),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','paid','shipped','canceled')),
  total NUMERIC(10,2) NOT NULL CHECK (total > 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON orders (user_id);
CREATE INDEX ON orders (created_at);
CREATE INDEX ON orders (status) WHERE status = 'pending';
```

## Queue Processing with SKIP LOCKED

```sql
UPDATE jobs
SET status = 'processing', worker_id = $1, started_at = now()
WHERE id = (
  SELECT id FROM jobs
  WHERE status = 'pending'
  ORDER BY created_at
  LIMIT 1
  FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

## Full-Text Search

```sql
ALTER TABLE articles ADD COLUMN search_vector TSVECTOR
  GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(title,'') || ' ' || coalesce(content,''))
  ) STORED;

CREATE INDEX ON articles USING GIN (search_vector);

SELECT *, ts_rank(search_vector, query) AS rank
FROM articles, to_tsquery('english', 'postgresql & performance') query
WHERE search_vector @@ query
ORDER BY rank DESC;
```
