# Azure Cosmos DB: Vector Search

Companion to `../SKILL.md`. Covers the integrated vector store in the NoSQL API: enabling the
feature, container vector policies, vector indexes, and `VectorDistance` queries.

## Enable the Feature

Vector indexing and search must be enabled on the account before any vector feature works
(portal: Settings > Features > "Vector Search for NoSQL API", or CLI):

```bash
az cosmosdb update \
    --resource-group <resource-group> \
    --name <account> \
    --capabilities EnableNoSQLVectorSearch
```

Registration is auto-approved but can take about 15 minutes to take effect. Not supported on
accounts with shared (database-level) throughput, and once enabled on a container it cannot be
disabled. ([Vector search](https://learn.microsoft.com/azure/cosmos-db/vector-search))

## Container Vector Policy

Each vector property needs an entry in the container's vector embedding policy. The policy cannot
be changed in place: you can add or remove path configurations, but to change a path's settings you
drop the policy or index entry and add it back.

```json
{
  "vectorEmbeddings": [
    {
      "path": "/embedding",
      "dataType": "float32",
      "distanceFunction": "cosine",
      "dimensions": 1536
    }
  ]
}
```

- `path`: one policy per path; wildcards and paths nested inside arrays are not supported.
- `dataType`: `float32`, `float16`, `int8`, or `uint8`. `float16` halves vector storage at a small
  accuracy cost.
- `distanceFunction`: `cosine` (default), `dotproduct`, or `euclidean`.
- `dimensions`: length of every vector at that path (default 1536).

## Vector Indexes

Add a `vectorIndexes` entry to the indexing policy, and exclude the vector path from the regular
index. Without the exclusion every insert also indexes the raw vector array as ordinary paths,
which raises write RU cost and latency.

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [{ "path": "/*" }],
  "excludedPaths": [
    { "path": "/_etag/?" },
    { "path": "/embedding/*" }
  ],
  "vectorIndexes": [
    { "path": "/embedding", "type": "diskANN" }
  ]
}
```

| Type | Search | Max dimensions | Pick when |
|------|--------|----------------|-----------|
| `flat` | Brute force, 100% recall | 505 | Small, exact searches |
| `quantizedFlat` | Brute force over compressed vectors | 4096 | Search scoped to roughly 50,000 vectors or fewer (filters, partition keys) |
| `diskANN` | Approximate nearest neighbor | 4096 | Larger sets; lowest latency and RU at high accuracy |

`quantizedFlat` and `diskANN` activate after at least 1,000 vectors are indexed; below that the
query falls back to a full scan with higher RU charges. `diskANN` is approximate: the same query
can return slightly different top-K results across runs, and recall is tunable per query via
`searchListSizeMultiplier` on `VectorDistance`. If you need exact results, use `flat`.

## Querying with VectorDistance

Parameterize the embedding, keep a `TOP N`, and order by the distance. Without `TOP N` the query
returns far more results and costs more RUs. In multi-tenant containers, filter by the partition
key so similarity search cannot cross tenants:

```sql
SELECT TOP 10 c.id, c.title, VectorDistance(c.embedding, @queryVector) AS score
FROM c
WHERE c.tenantId = @tenantId
ORDER BY VectorDistance(c.embedding, @queryVector)
```

Run it through the SDK's parameterized-query API shown in each language reference
(`query_items` / `queryItems` / `items.query`). Vector RU cost varies widely with index type,
dimensions, and `TOP N`; check the request charge on responses while tuning policy and index
choices. ([VectorDistance](https://learn.microsoft.com/cosmos-db/query/vectordistance))

## Hybrid Search (Vector + Full-Text)

Combine `VectorDistance` with BM25 scoring through the `RRF` system function in an
`ORDER BY RANK` clause; an optional weights array biases the fusion:

```sql
SELECT TOP 10 *
FROM c
ORDER BY RANK RRF(
    VectorDistance(c.embedding, @queryVector),
    FullTextScore(c.text, @term1, @term2),
    [2, 1]
)
```

Requires the vector feature plus a full-text policy and index on the container; see
`full-text-search.md`. ([Hybrid search](https://learn.microsoft.com/azure/cosmos-db/gen-ai/hybrid-search))
