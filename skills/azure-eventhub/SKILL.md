---
name: azure-eventhub
description: >-
  Azure Event Hubs polyglot development. High-throughput event streaming
  with C#, Java, Python, TypeScript, and Rust SDKs. Use when building or
  reviewing Azure Event Hubs solutions: producers, consumers, checkpointing,
  partitions, consumer groups, throughput tuning, or SDK code.
---

# Azure Event Hubs -- Polyglot Skill

> **Shared Knowledge**: This skill builds on `brain/knowledge/general-problem-solving.md`, `brain/knowledge/coding-general.md`, `brain/knowledge/devops-operations.md`, and `brain/knowledge/testing.md`. Always apply those principles alongside the specific guidance below.

You are an expert Azure Event Hubs developer. You help build high-throughput event streaming applications using the Event Hubs SDKs for C# (.NET), Java, Python, TypeScript, and Rust. You know AMQP internals, partition strategies, checkpointing, consumer groups, Schema Registry, Kafka compatibility, and Event Grid integration. You write production-grade code with proper authentication, error handling, retry policies, and performance tuning.

## Core Concepts

- **Namespace**: DNS-scoped container (`<name>.servicebus.windows.net`) hosting one or more Event Hubs. Throughput units (Standard) or processing units (Premium/Dedicated) control capacity.
- **Event Hub**: A partitioned, append-only log. Each hub has 1-32 partitions (Standard) or up to 2000 (Dedicated).
- **Partition**: Ordered, immutable sequence of events. Events are retained for 1-90 days. Each partition is consumed independently.
- **Consumer Group**: A view of the entire Event Hub. Each group tracks its own offsets. Maximum 5 per hub (Standard) or 20 (Premium). Default: `$Default`.
- **AMQP 1.0**: The wire protocol. SDKs abstract this; understand it for debugging connection/link errors and credit-based flow control.
- **Checkpointing**: Storing the last successfully processed offset per partition per consumer group. Backed by Azure Blob Storage.
- **Partition Key**: Hash-based routing. Events with the same key always go to the same partition, guaranteeing ordering for that key.

## Installation

Per-language install commands and package names: see `references/csharp.md`, `references/java.md`, `references/python.md`, `references/typescript.md`, `references/rust.md`.

## Environment Variables

```bash
EVENTHUB_FULLY_QUALIFIED_NAMESPACE=<namespace>.servicebus.windows.net
EVENTHUB_NAME=<event-hub-name>
BLOB_STORAGE_CONNECTION_STRING=<storage-connection-string>  # Checkpointing
BLOB_CONTAINER_NAME=checkpoints
# Alternative (not recommended for production):
EVENTHUB_CONNECTION_STRING=Endpoint=sb://<namespace>.servicebus.windows.net/;SharedAccessKeyName=...
```

## Authentication

Always use `DefaultAzureCredential` (or equivalent) in production. Connection strings are acceptable only for local development.

Per-language client authentication: see `references/csharp.md`, `references/java.md`, `references/python.md`, `references/typescript.md`, `references/rust.md`.

**Required RBAC Roles**:
- Sending: `Azure Event Hubs Data Sender`
- Receiving: `Azure Event Hubs Data Receiver`
- Both: `Azure Event Hubs Data Owner`

## Client Types

| Language | Producer | Consumer (simple) | Consumer (production) |
|----------|----------|-------------------|----------------------|
| C# | `EventHubProducerClient`, `EventHubBufferedProducerClient` | `EventHubConsumerClient` | `EventProcessorClient` |
| Java | `EventHubProducerClient` / `AsyncClient` | `EventHubConsumerClient` / `AsyncClient` | `EventProcessorClient` |
| Python | `EventHubProducerClient` | `EventHubConsumerClient` | `EventHubConsumerClient` + `BlobCheckpointStore` |
| TypeScript | `EventHubProducerClient` | `EventHubConsumerClient` | `EventHubConsumerClient` + `BlobCheckpointStore` |
| Rust | `ProducerClient` | `ConsumerClient` | `ConsumerClient` + checkpoint store |

**Rule**: Never use a simple consumer client in production. Always use the processor/checkpoint-backed variant.

## Producer Patterns

### Batch Send (All Languages)

Always use batch APIs. They respect the 1 MB message size limit automatically. The try-add / send-when-full / re-add pattern is identical across languages; canonical C# example:

```csharp
await using var producer = new EventHubProducerClient(ns, hub, new DefaultAzureCredential());
using EventDataBatch batch = await producer.CreateBatchAsync();

foreach (var item in items)
{
    if (!batch.TryAdd(new EventData(BinaryData.FromString(JsonSerializer.Serialize(item)))))
    {
        await producer.SendAsync(batch);
        batch = await producer.CreateBatchAsync();
        if (!batch.TryAdd(new EventData(BinaryData.FromString(JsonSerializer.Serialize(item)))))
            throw new Exception("Single event exceeds max batch size");
    }
}
if (batch.Count > 0) await producer.SendAsync(batch);
```

Java, Python, TypeScript, and Rust batch-send variants: see `references/java.md`, `references/python.md`, `references/typescript.md`, `references/rust.md`.

### Buffered Producer (C# Only)

For high-volume fire-and-forget with automatic background batching: see `references/csharp.md`.

### Partition Routing

```csharp
// By partition key (recommended -- preserves ordering for a logical group)
var batch = await producer.CreateBatchAsync(new CreateBatchOptions { PartitionKey = "customer-123" });

// By partition ID (use sparingly -- bypasses load balancing)
var batch = await producer.CreateBatchAsync(new CreateBatchOptions { PartitionId = "0" });
```

Pattern is identical across languages: pass `partition_key` / `partitionKey` / `setPartitionKey()` on batch options.

## Consumer Patterns

### Production Consumer with Checkpointing

**C#** -- `EventProcessorClient`:
```csharp
var blobClient = new BlobContainerClient(storageConnStr, containerName);
await blobClient.CreateIfNotExistsAsync();

var processor = new EventProcessorClient(blobClient,
    EventHubConsumerClient.DefaultConsumerGroup, ns, hub, new DefaultAzureCredential());

processor.ProcessEventAsync += async args =>
{
    Console.WriteLine($"Partition {args.Partition.PartitionId}: {args.Data.EventBody}");
    await args.UpdateCheckpointAsync();
};
processor.ProcessErrorAsync += args =>
{
    Console.Error.WriteLine($"Error on {args.PartitionId}: {args.Exception.Message}");
    return Task.CompletedTask;
};

await processor.StartProcessingAsync();
await Task.Delay(Timeout.Infinite, cancellationToken);
await processor.StopProcessingAsync();
```

Java, Python, TypeScript, and Rust production-consumer variants (checkpoint-backed): see `references/java.md`, `references/python.md`, `references/typescript.md`, `references/rust.md`.

## Checkpointing Strategies

| Strategy | When to Use | Trade-off |
|----------|-------------|-----------|
| Every event | Low volume, critical data (e.g., financial) | Highest reliability, lowest throughput |
| Every N events | Balanced throughput and reliability | Some reprocessing on failure |
| Time-based interval | Consistent checkpoint cadence | Predictable storage cost |
| After logical batch | Processing grouped events | Natural boundary, minimal waste |

## Error Handling

Per-language error-handling examples (transient vs. non-transient): see `references/csharp.md`, `references/java.md`.

**Key rule**: Never checkpoint on processing failure. Let events be redelivered.

## Performance Tuning

| Lever | Recommendation |
|-------|----------------|
| Partitions | More partitions = more parallelism. Size for peak throughput. Cannot reduce after creation. |
| Batch size | Maximize batch fill before sending. Use buffered producer (C#) for automatic optimization. |
| Prefetch | Increase prefetch count for high-throughput consumers to reduce round-trips. |
| Connection pooling | Reuse clients as singletons. Creating clients is expensive (AMQP connection setup). |
| Checkpointing frequency | Reduce checkpoint frequency to improve throughput (trade-off: more reprocessing on failure). |
| Consumer parallelism | One consumer instance per partition. Scale consumers = scale partitions. |
| Compression | Compress event payloads (gzip/snappy) at application level before sending. |
| Throughput units | Scale namespace TUs (Standard) or PUs (Premium) to match ingestion rate. |

## Kafka Compatibility

Event Hubs exposes a Kafka-compatible endpoint (Standard tier and above). Use any Kafka client with:

```properties
bootstrap.servers=<namespace>.servicebus.windows.net:9093
security.protocol=SASL_SSL
sasl.mechanism=PLAIN
sasl.jaas.config=org.apache.kafka.common.security.plain.PlainLoginModule required \
  username="$ConnectionString" \
  password="<connection-string>";
```

## Schema Registry

Azure Schema Registry (part of Event Hubs namespace) stores Avro schemas. SDKs provide Avro serializers that automatically register and validate schemas.

Use Schema Registry when you need schema evolution, backward/forward compatibility, and cross-team contract enforcement.

## IaC -- Infrastructure as Code

Bicep and Terraform provisioning examples: see `references/iac.md`.

## Anti-Patterns

| Anti-Pattern | Why It Is Wrong | Correct Approach |
|--------------|----------------|------------------|
| Using simple consumer in production | No checkpointing, no load balancing, no failover | Use EventProcessorClient or checkpoint-backed consumer |
| Sending events without batching | Inefficient, more network calls, higher cost | Always use batch APIs |
| Checkpointing before processing | Data loss on failure | Checkpoint after successful processing |
| Hardcoding partition IDs in consumers | Breaks when partitions change, no load balancing | Let the processor manage partition assignment |
| Ignoring error handlers | Silent failures, stuck consumers | Always register error handlers and log/alert |
| Using connection strings in production | Security risk, no rotation, no audit trail | Use Managed Identity with RBAC |
