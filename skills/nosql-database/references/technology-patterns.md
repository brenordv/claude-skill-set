# NoSQL: Per-Technology Pattern Reference

Companion to `nosql-database/SKILL.md`. Engine-specific patterns for each NoSQL
technology. For Azure Cosmos DB specifics, use the `azure-cosmos` skill.

## MongoDB-specific patterns

- Use compound indexes matching query predicates (equality fields first, sort fields, range fields last)
- Aggregation pipeline for complex transformations (prefer `$match` and `$project` early to reduce pipeline data)
- Use `$lookup` sparingly; it is a server-side JOIN and undermines document model benefits
- Schema validation with JSON Schema for data integrity without rigid migrations
- Change streams for real-time event-driven architectures
- Sharding: choose shard key with high cardinality, distribute writes evenly, avoid scatter-gather queries

## Redis-specific patterns

- Data structures: Strings, Hashes, Lists, Sets, Sorted Sets, Streams, HyperLogLog
- Use Hashes for object storage instead of serialized JSON strings (partial field access)
- Sorted Sets for leaderboards, priority queues, time-series with score-based queries
- Redis Streams for event log and message broker patterns
- Pub/Sub for real-time notifications (fire-and-forget, not durable)
- Cluster mode for horizontal scaling; hash slots distribute keys across nodes
- Persistence: RDB snapshots for point-in-time, AOF for durability; combine both in production
- Eviction policies: `allkeys-lru` for cache, `noeviction` for data store
- Pipeline commands to reduce round trips; use MULTI/EXEC for atomic operations

## DynamoDB-specific patterns

- Single-table design: store multiple entity types in one table using composite keys
- Partition Key (PK) + Sort Key (SK) enable hierarchical and relational queries within a partition
- GSI (Global Secondary Index): alternative query views; eventually consistent
- LSI (Local Secondary Index): alternative sort within same partition; must be defined at creation
- WCU/RCU capacity planning: on-demand for unpredictable, provisioned for steady workloads
- TTL attribute for automatic data expiration without tombstone overhead
- DynamoDB Streams for change data capture and event-driven processing
- Transactions: `TransactWriteItems` and `TransactGetItems` for ACID across up to 100 items

## Cassandra-specific patterns

- No JOINs, no aggregations: pre-compute aggregates in separate counter tables
- **Avoid `ALLOW FILTERING`** in production; it means a full cluster scan and your model is wrong
- Writes are cheap: append-only LSM tree architecture; optimize for read efficiency
- Tombstones: deletes create expensive markers; avoid high-velocity delete patterns (queues)
- Lightweight Transactions (LWT) for conditional inserts/updates; use sparingly (consensus overhead)
- Repair and compaction strategies are critical for long-running clusters
- Tunable consistency: `ONE`, `QUORUM`, `ALL` per query; `LOCAL_QUORUM` for multi-DC

## Neo4j-specific patterns

- Cypher query language: `MATCH (u:User)-[:FOLLOWS]->(f:User) RETURN f`
- Index node properties used in `MATCH` or `WHERE` clauses
- Use relationship types to encode meaning: `:PURCHASED`, `:REVIEWED`, `:FOLLOWS`
- APOC library for advanced algorithms (shortest path, page rank, community detection)
- Avoid unbounded variable-length path queries without limits: `[:KNOWS*1..5]` not `[:KNOWS*]`
