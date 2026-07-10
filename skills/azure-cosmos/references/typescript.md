# Azure Cosmos DB: TypeScript SDK

Companion to `../SKILL.md`. Concepts, tables, and rules live in the skill body; this file holds the TypeScript/JavaScript code.

## Installation

```bash
npm install @azure/cosmos @azure/identity
```

## Authentication

```typescript
import { CosmosClient } from "@azure/cosmos";
import { DefaultAzureCredential } from "@azure/identity";

const client = new CosmosClient({
  endpoint: process.env.COSMOS_ENDPOINT!,
  aadCredentials: new DefaultAzureCredential(),
});
```

## CRUD Operations

### Create
```typescript
// TypeScript
const { resource } = await container.items.create<Item>(item);
```

### Read (Point Read - most efficient, 1 RU for 1KB)
```typescript
// TypeScript
const { resource } = await container.item("1", "A").read<Item>();
```

### Upsert (Idempotent - prefer over create for retry safety)
```typescript
// TypeScript
const { resource } = await container.items.upsert<Item>(item);
```

### Patch (Partial Update - lower RU than full replace)
```typescript
// TypeScript
const ops: PatchOperation[] = [
  { op: "replace", path: "/price", value: 799.99 },
  { op: "add", path: "/discount", value: true },
  { op: "remove", path: "/oldField" },
];
await container.item("1", "A").patch<Item>(ops);
```

## Queries

### Parameterized Queries (ALWAYS use parameters - never string concatenation)
```typescript
// TypeScript
const querySpec: SqlQuerySpec = {
  query: "SELECT * FROM c WHERE c.partitionKey = @cat AND c.price < @max",
  parameters: [
    { name: "@cat", value: "electronics" },
    { name: "@max", value: 1000 },
  ],
};
const { resources } = await container.items.query<Item>(querySpec).fetchAll();
```

### Cross-Partition Queries
```typescript
// TypeScript
container.items.query<Item>(query, { enableCrossPartitionQuery: true }).fetchAll();
```

### Pagination
```typescript
// TypeScript
const iterator = container.items.query<Item>(querySpec, { maxItemCount: 10 });
while (iterator.hasMoreResults()) {
  const { resources, continuationToken } = await iterator.fetchNext();
}
```

## Bulk Operations

```typescript
import { BulkOperationType, OperationInput } from "@azure/cosmos";

const operations: OperationInput[] = [
  { operationType: BulkOperationType.Create, resourceBody: item1 },
  { operationType: BulkOperationType.Upsert, resourceBody: item2 },
  { operationType: BulkOperationType.Delete, id: "3", partitionKey: "pk" },
];

const response = await container.items.executeBulkOperations(operations);
response.forEach((result, i) => {
  if (result.statusCode < 200 || result.statusCode >= 300) {
    console.error(`Operation ${i} failed: ${result.statusCode}`);
  }
});
```

## Service Layer Pattern

```typescript
export class ItemService {
  private container: Container;

  constructor(client: CosmosClient) {
    this.container = client
      .database(process.env.COSMOS_DATABASE!)
      .container(process.env.COSMOS_CONTAINER!);
  }

  async getById(id: string, pk: string): Promise<Item | null> {
    try {
      const { resource } = await this.container.item(id, pk).read<Item>();
      return resource ?? null;
    } catch (error) {
      if (error instanceof ErrorResponse && error.code === 404) return null;
      throw error;
    }
  }
}
```
