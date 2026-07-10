# Azure Event Hubs: C# (.NET) SDK

Companion to `../SKILL.md`. Concepts, tables, and rules live in the skill body; this file holds the C# code. The canonical batch-send and production-consumer examples live inline in `../SKILL.md`.

## Installation

```bash
dotnet add package Azure.Messaging.EventHubs            # Core
dotnet add package Azure.Messaging.EventHubs.Processor  # Production consumer
dotnet add package Azure.Identity                       # Auth
dotnet add package Azure.Storage.Blobs                  # Checkpointing
```

## Authentication

```csharp
var credential = new DefaultAzureCredential();
var producer = new EventHubProducerClient(
    fullyQualifiedNamespace, eventHubName, credential);
```

## Producer: Batch Send

Canonical C# batch-send example: see `../SKILL.md` (Producer Patterns → Batch Send).

### Buffered Producer (C# Only)

For high-volume fire-and-forget with automatic background batching:

```csharp
await using var producer = new EventHubBufferedProducerClient(ns, hub, credential,
    new EventHubBufferedProducerClientOptions { MaximumWaitTime = TimeSpan.FromSeconds(1) });

producer.SendEventBatchSucceededAsync += args => { /* log success */ return Task.CompletedTask; };
producer.SendEventBatchFailedAsync += args => { /* log failure */ return Task.CompletedTask; };

for (int i = 0; i < 10000; i++)
    await producer.EnqueueEventAsync(new EventData($"Event {i}"));

await producer.FlushAsync();
```

## Consumer: Production with Checkpointing

Canonical C# `EventProcessorClient` example: see `../SKILL.md` (Consumer Patterns → Production Consumer with Checkpointing).

## Error Handling

```csharp
try { await producer.SendAsync(batch); }
catch (EventHubsException ex) when (ex.IsTransient) { /* safe to retry with backoff */ }
catch (EventHubsException ex) when (ex.Reason == EventHubsException.FailureReason.ServiceBusy)
{ await Task.Delay(TimeSpan.FromSeconds(5)); }
catch (EventHubsException ex) { /* non-transient: log and alert */ }
```
