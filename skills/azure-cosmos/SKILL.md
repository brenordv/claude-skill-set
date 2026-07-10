---
name: azure-cosmos
description: >-
  Polyglot Azure Cosmos DB development. NoSQL API, data modeling, production
  patterns. Supports Python, Java, TypeScript, and Rust SDKs. Use when building
  or reviewing Azure Cosmos DB (NoSQL API) solutions: data modeling, partition
  keys, RU/cost optimization, queries, consistency, or SDK code.
---

# Azure Cosmos DB

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md`, `brain/knowledge/coding-general.md`, `brain/knowledge/database.md`, and `brain/knowledge/testing.md`. Always apply those principles alongside the specific guidance below.

You are an expert Azure Cosmos DB developer and architect. You design and implement production-grade Cosmos DB solutions across Python, Java, TypeScript, and Rust SDKs. You prioritize security (RBAC over keys), performance (partition-aware operations), cost efficiency (RU optimization), and clean architecture (service layer separation). You never use string concatenation in queries, always specify partition keys, and design data models around access patterns.

## Installation

Per-language install commands and package notes: see `references/python.md`, `references/java.md`, `references/typescript.md`, `references/rust.md`.

## Environment Variables

```bash
COSMOS_ENDPOINT=https://<account>.documents.azure.com:443/
COSMOS_DATABASE=<database-name>
COSMOS_CONTAINER=<container-name>
# For key-based auth only (prefer RBAC/AAD in production)
COSMOS_KEY=<account-key>
```

## Authentication

**Always prefer DefaultAzureCredential / Entra ID over keys in production.** Keys are acceptable only for local emulator development.

Per-language client setup (production AAD/RBAC, async, emulator): see `references/python.md`, `references/java.md`, `references/typescript.md`, `references/rust.md`.

## Resource Hierarchy

```
CosmosClient (Account-level)
└── Database
    └── Container
        ├── Items (documents)
        ├── Scripts (stored procedures, triggers, UDFs)
        └── Conflicts
```

| Language | Account Client | Database Client | Container Client |
|----------|---------------|-----------------|------------------|
| Python | `CosmosClient` | `DatabaseProxy` | `ContainerProxy` |
| Java | `CosmosClient` / `CosmosAsyncClient` | `CosmosDatabase` / `CosmosAsyncDatabase` | `CosmosContainer` / `CosmosAsyncContainer` |
| TypeScript | `CosmosClient` | `Database` | `Container` |
| Rust | `CosmosClient` | `DatabaseClient` | `ContainerClient` |

## Core Concepts

### Partition Keys
The single most important design decision. Data is distributed across physical partitions based on the partition key.

**Selection criteria:**
- High cardinality (many distinct values)
- Even distribution of data AND request volume
- Frequently used in WHERE clauses
- Avoids hot partitions (do not use low-cardinality keys like `status` or `country`)

**Hierarchical partition keys** (multi-level) for multi-tenant scenarios:
```typescript
// TypeScript
partitionKey: {
  paths: ["/tenantId", "/userId", "/sessionId"],
  version: PartitionKeyDefinitionVersion.V2,
  kind: PartitionKeyKind.MultiHash,
}
```
```python
# Python
partition_key=PartitionKey(path=["/tenant_id", "/user_id"])
```

### Request Units (RU/s)
All operations consume RUs. A point read of a 1KB document costs 1 RU. Always check response headers:
```python
# Python
response = container.create_item(body=item)
# Check headers for request charge
```
```java
// Java
CosmosItemResponse<User> response = container.createItem(user);
System.out.println("RU charge: " + response.getRequestCharge());
```

### Consistency Levels (weakest to strongest)
| Level | Guarantee | RU Cost | Use Case |
|-------|-----------|---------|----------|
| Eventual | No ordering guarantee | Lowest | Analytics, non-critical reads |
| Consistent Prefix | Reads never see out-of-order writes | Low | Display feeds, timelines |
| Session | Consistent within client session | Medium | **Default. Best for most apps** |
| Bounded Staleness | Bounded lag (time or operations) | High | Financial dashboards |
| Strong | Linearizability (global) | Highest | Multi-region ACID requirements |

### Global Distribution
- Multi-region writes with automatic conflict resolution (LWW, custom, or merge procedures)
- Configure preferred regions in client for lowest latency reads
- Use Session consistency for single-region; Bounded Staleness or Strong for multi-region critical reads

## CRUD Operations

- **Create**
- **Read (Point Read - most efficient, 1 RU for 1KB)**: requires `id` AND partition key
- **Upsert (Idempotent - prefer over create for retry safety)**
- **Patch (Partial Update - lower RU than full replace)**
- **Delete**

Per-language CRUD examples: see `references/python.md`, `references/java.md`, `references/typescript.md`, `references/rust.md`.

## Queries

### Parameterized Queries (ALWAYS use parameters - never string concatenation)

Pass the partition key for single-partition queries; use `maxItemCount` + continuation tokens for pagination.

Per-language query examples (parameterized, cross-partition, pagination): see `references/python.md`, `references/java.md`, `references/typescript.md`.

## Bulk Operations

Per-language bulk-operation examples: see `references/typescript.md`.

## Data Modeling

### Embedding vs. Referencing

| Strategy | When to Use | Trade-off |
|----------|-------------|-----------|
| **Embed** (denormalize) | Data read together, bounded child arrays, 1:few relationships | Faster reads, larger documents, update complexity |
| **Reference** (normalize) | Unbounded relationships, independently accessed data, 1:many or many:many | Extra reads, smaller documents, simpler updates |

**Embed** when child data is bounded and always read with parent:
```json
{
  "id": "order-1", "customerId": "C1",
  "items": [
    {"sku": "A1", "qty": 2, "price": 10.00},
    {"sku": "B2", "qty": 1, "price": 25.00}
  ]
}
```

**Reference** when child data is unbounded or independently queried:
```json
{"id": "order-1", "customerId": "C1", "total": 45.00}
{"id": "item-1", "orderId": "order-1", "sku": "A1", "qty": 2}
```

### Denormalization and Duplication
Duplicate data across containers to serve different access patterns. Manage consistency via change feed or transactional batch.

### Document Type Discrimination
Store multiple entity types in one container using a `docType` or `type` field:
```json
{"id": "u1", "type": "user", "pk": "tenant-1", "name": "Alice"}
{"id": "o1", "type": "order", "pk": "tenant-1", "userId": "u1", "total": 50}
```
Query: `SELECT * FROM c WHERE c.pk = 'tenant-1' AND c.type = 'order'`

## Indexing Policies

Default policy indexes all properties. Customize for performance and RU savings:

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    { "path": "/name/?" },
    { "path": "/category/?" },
    { "path": "/price/?" }
  ],
  "excludedPaths": [
    { "path": "/largeBlob/*" },
    { "path": "/_etag/?" }
  ],
  "compositeIndexes": [
    [
      { "path": "/category", "order": "ascending" },
      { "path": "/price", "order": "descending" }
    ]
  ],
  "spatialIndexes": [
    { "path": "/location/*", "types": ["Point", "Polygon"] }
  ]
}
```

**Rules:**
- Exclude paths not used in WHERE, ORDER BY, or JOIN to reduce write RU cost
- Add composite indexes for ORDER BY on multiple fields
- Use range indexes (default) for equality and range filters
- Spatial indexes for geospatial queries

## Change Feed

Process real-time changes to documents (creates and updates, not deletes by default).

**Use cases:** Event-driven architectures, materialized views, data synchronization, analytics pipelines, search index updates.

**Processing models:**
- Azure Functions trigger (simplest)
- Change feed processor library (SDK-based, with leases)
- Change feed pull model (manual control)

## TTL (Time to Live)

Auto-expire documents to save storage and RU costs:

```json
{
  "defaultTtl": 86400,
  "id": "session-1",
  "ttl": 3600
}
```
- Container-level `defaultTtl`: -1 (enabled, no default), or seconds
- Item-level `ttl`: overrides container default; -1 means never expire

## Stored Procedures, Triggers, and UDFs

- **Stored procedures:** JavaScript, execute within a single partition key, provide ACID transactions
- **Pre/Post triggers:** Attach to create/replace/delete operations
- **UDFs:** Custom functions usable in SQL queries
- Stored procedures are scoped to a single partition key -- they cannot span partitions

## Optimistic Concurrency (ETags)

```typescript
// TypeScript
const { resource, etag } = await container.item("1", "pk").read<Item>();
resource.price = 899.99;
try {
  await container.item("1", "pk").replace(resource, {
    accessCondition: { type: "IfMatch", condition: etag },
  });
} catch (error) {
  if (error instanceof ErrorResponse && error.code === 412) {
    // Document modified by another process - re-read and retry
  }
}
```

## Error Handling

| Status Code | Meaning | Action |
|-------------|---------|--------|
| 400 | Bad request | Fix query syntax or document structure |
| 404 | Not found | Return null/empty, check id and partition key |
| 409 | Conflict | Item already exists; use upsert if appropriate |
| 412 | Precondition failed | ETag mismatch; re-read and retry |
| 429 | Rate limited | Retry with backoff (SDK has built-in retry) |
| 449 | Transient write conflict | Retry (SDK handles automatically) |

Per-language error-handling examples: see `references/python.md`, `references/java.md`.

## Throughput Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| Provisioned | Fixed RU/s, billed per hour | Predictable workloads |
| Autoscale | 10%-100% of max RU/s | Variable workloads with peaks |
| Serverless | Pay per request | Dev/test, low/sporadic traffic |

```python
# Python - Provisioned
container = database.create_container_if_not_exists(
    id="mycontainer", partition_key=PartitionKey(path="/pk"), offer_throughput=400
)
# Read and update throughput
offer = container.read_offer()
container.replace_throughput(throughput=1000)
```

## Service Layer Pattern

Per-language service-layer examples: see `references/python.md` (FastAPI), `references/typescript.md`.

## Pydantic Model Pattern (Python)

Five-tier model hierarchy for clean API design. See `references/python.md`.

## Testing

### Python (pytest)
See `references/python.md`.

### TypeScript (Jest/Vitest)
Mock the `CosmosClient` and container methods. Test service layer in isolation.

### Integration Testing
Use the Cosmos DB Emulator (`https://localhost:8081`) for local integration tests. The emulator supports the NoSQL API with a well-known key.

## Infrastructure as Code

Bicep and Terraform provisioning examples: see `references/iac.md`.

## Multi-API Support

Cosmos DB supports multiple APIs. Choose based on existing ecosystem and workload:

| API | Wire Protocol | Best For |
|-----|---------------|----------|
| **NoSQL** (Core SQL) | Native REST | New projects, flexible schema, SQL-like queries |
| **MongoDB** | MongoDB wire protocol | MongoDB migration, MongoDB tooling ecosystem |
| **Cassandra** | CQL wire protocol | Cassandra migration, wide-column workloads |
| **Gremlin** | Apache TinkerPop | Graph traversals, relationship-heavy data |
| **Table** | Azure Table Storage | Key-value, Table Storage migration |

All APIs share the same underlying engine, global distribution, and SLAs. The NoSQL API provides the richest feature set.

## Monitoring and Diagnostics

**Key metrics to track:**
- RU consumption per operation and per partition
- 429 (throttling) rate
- Latency (P50, P95, P99)
- Storage utilization per partition (detect hot partitions)
- Availability and replication lag

**Tools:** Azure Monitor, Azure Diagnostics Logs, Application Insights, SDK-level diagnostics headers.

## Backup and Restore

| Mode | Description |
|------|-------------|
| Periodic | Automatic backups at configured intervals (default: 4hrs, 8 copies) |
| Continuous | Point-in-time restore to any second within retention period (7 or 30 days) |

Use continuous backup for production workloads requiring granular recovery.

## Conflict Resolution (Multi-Region Writes)

| Policy | Behavior |
|--------|----------|
| Last Writer Wins (LWW) | Highest `_ts` (or custom path) wins. Default. |
| Custom | Merge procedure (stored procedure) resolves conflicts |
| Async | Conflicts written to conflict feed for manual resolution |

## Performance Best Practices

1. **Use direct mode** (Java/TypeScript) for lowest latency in production
2. **Prefer point reads** (`read_item`) over queries for single-document retrieval (1 RU for 1KB)
3. **Always specify partition key** in read and query operations
4. **Use async clients** for high-throughput scenarios (Python `aio`, Java `CosmosAsyncClient`)
5. **Batch operations** within the same partition key for transactional guarantees
6. **Use patch** for partial updates instead of read-modify-replace
7. **Configure preferred regions** in multi-region deployments
8. **Use upsert** for idempotent writes (safe for retries)
9. **Enable content response on write** (Java) for immediate access to written items

## Cost Optimization

1. **Right-size throughput** -- use autoscale for variable loads, serverless for dev/test
2. **Optimize indexing** -- exclude unused paths to reduce write RU cost
3. **Use TTL** to auto-expire stale data
4. **Use projections** (`SELECT c.id, c.name`) instead of `SELECT *`
5. **Use reserved capacity** for predictable production workloads (up to 65% savings)

## Security Checklist

- [ ] Validate partition key access matches user authorization (tenant isolation)
- [ ] Configure RBAC roles (Cosmos DB Built-in Data Reader/Contributor)
- [ ] Use private endpoints / VNet integration for network isolation

## Anti-Patterns

- **Using low-cardinality partition keys** (e.g., `status`, `country`) -- creates hot partitions
- **Cross-partition queries as default** -- design data model to avoid them
- **Unbounded arrays in documents** -- embed only bounded child data; reference unbounded collections
- **SELECT * without projection** -- wastes RU on unused fields
- **Ignoring 429 responses** -- implement retry with exponential backoff (SDKs have built-in retry)
- **One container per entity type** -- use document type discrimination in shared containers where access patterns align
- **Scatter-gather reads** -- querying all partitions to find one item
- **Not checking RU costs** -- monitor per-operation RU charge during development
- **String concatenation in queries** -- injection risk and prevents plan caching
