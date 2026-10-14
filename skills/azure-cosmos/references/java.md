# Azure Cosmos DB: Java SDK

Companion to `../SKILL.md`. Concepts, tables, and rules live in the skill body; this file holds the Java code.

## Installation

```xml
<dependency>
    <groupId>com.azure</groupId>
    <artifactId>azure-cosmos</artifactId>
    <version>LATEST</version>
</dependency>
```
Use Azure SDK BOM for version management: `azure-sdk-bom`.

## Authentication

```java
// Sync client
CosmosClient client = new CosmosClientBuilder()
    .endpoint(System.getenv("COSMOS_ENDPOINT"))
    .credential(new DefaultAzureCredentialBuilder().build())
    .consistencyLevel(ConsistencyLevel.SESSION)
    .contentResponseOnWriteEnabled(true)
    .preferredRegions(Arrays.asList("West US", "East US"))
    .directMode()
    .buildClient();

// Async client (high-throughput)
CosmosAsyncClient asyncClient = new CosmosClientBuilder()
    .endpoint(serviceEndpoint)
    .credential(new DefaultAzureCredentialBuilder().build())
    .buildAsyncClient();
```

## Client Configuration and Resilience

`CosmosClient` and `CosmosAsyncClient` are thread-safe; keep a single instance for the application
lifetime. The builder defaults to direct mode, and `contentResponseOnWriteEnabled` defaults to
false, so writes return headers and status only: enable it when you need the written item back,
leave it off in write-heavy paths to save serialization and bandwidth.
([CosmosClientBuilder](https://learn.microsoft.com/java/api/com.azure.cosmos.cosmosclientbuilder))

Throttling retries are configured with `throttlingRetryOptions(...)` on the builder. Retries are
silent: a `CosmosException` with status 429 means they were exhausted, so watch the 429 metric when
tuning them up. On errors (and on suspiciously slow successes) log `getDiagnostics()` along with
the status code, sub-status, activity id, and request charge.

### Pagination and Batched Reads

`byPage(continuationToken, pageSize)` continues from a token; pass `null` for the first page, and
normalize empty strings to `null` before the call (transport layers that default an absent string
to `""` would otherwise pass an invalid token). Each `FeedResponse` page carries
`getRequestCharge()`; sum across pages for the query's real cost.

For batched lookups by known `(id, partitionKey)` pairs, use
`readMany(List<CosmosItemIdentity>, Class<T>)` on the container: it targets only the relevant
partitions instead of fanning out like an `IN` list spanning partition keys.
([CosmosAsyncContainer](https://learn.microsoft.com/java/api/com.azure.cosmos.cosmosasynccontainer))
Of this skill's languages only Java has `readMany`; elsewhere use bounded parallel point reads.

## CRUD Operations

### Create
```java
// Java
container.createItem(new Item("1", "A", "Item"));
```

### Read (Point Read - most efficient, 1 RU for 1KB)
```java
// Java
container.readItem("1", new PartitionKey("A"), Item.class);
```

## Queries

### Parameterized Queries (ALWAYS use parameters - never string concatenation)
```java
// Java
String query = "SELECT * FROM c WHERE c.status = @status";
CosmosPagedIterable<Item> results = container.queryItems(query, options, Item.class);
```

## Error Handling

```java
// Java
try {
    container.createItem(item);
} catch (CosmosException e) {
    if (e.getStatusCode() == 429) {
        Duration retryAfter = e.getRetryAfterDuration();
    }
}
```
