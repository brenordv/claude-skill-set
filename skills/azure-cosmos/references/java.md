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
