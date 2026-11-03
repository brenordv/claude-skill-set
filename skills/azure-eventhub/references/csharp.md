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
producer.SendEventBatchFailedAsync += async args =>
{
    if (args.Exception is EventHubsException { IsTransient: true } && !args.CancellationToken.IsCancellationRequested)
    {
        await producer.EnqueueEventsAsync(args.EventBatch, args.CancellationToken);
        return;
    }

    if (!await deadLetterStore.TryParkAsync(args.EventBatch, CancellationToken.None))
    {
        logger.LogCritical(args.Exception, "Parking failed, {EventCount} events lost. Partition: [{PartitionId}]",
            args.EventBatch.Count, args.PartitionId);
        return;
    }

    logger.LogError(args.Exception, "Parked {EventCount} events. Partition: [{PartitionId}]",
        args.EventBatch.Count, args.PartitionId);
};

for (int i = 0; i < 10000; i++)
    await producer.EnqueueEventAsync(new EventData($"Event {i}"));

await producer.FlushAsync();
```

`SendEventBatchFailedAsync` runs only after the retry policy is exhausted, and the caller of
`EnqueueEventAsync` never sees the failure, so the handler is where a batch is saved or lost.
Re-enqueued events go to the end of the buffer, so their order is lost
([SendEventBatchFailedAsync](https://learn.microsoft.com/en-us/dotnet/api/azure.messaging.eventhubs.producer.eventhubbufferedproducerclient.sendeventbatchfailedasync)).
A non-transient failure, or one while the producer is closing (`args.CancellationToken` signals
that, per
[SendEventBatchFailedEventArgs.CancellationToken](https://learn.microsoft.com/en-us/dotnet/api/azure.messaging.eventhubs.producer.sendeventbatchfailedeventargs.cancellationtoken)),
is parked instead of looping through the buffer forever.

## Consumer: Production with Checkpointing

Canonical C# `EventProcessorClient` example: see `../SKILL.md` (Consumer Patterns → Production Consumer with Checkpointing).

## Error Handling

```csharp
try
{
    await producer.SendAsync(batch, cancellationToken);
}
catch (EventHubsException ex)
{
    throw new EventPublishException($"Sending a batch of {batch.Count} events failed", ex);
}
```

The client applies its retry policy (`EventHubProducerClientOptions.RetryOptions`) before an
exception surfaces, so `IsTransient == true` here means those retries already ran out
([troubleshooting guide](https://github.com/Azure/azure-sdk-for-net/blob/main/sdk/eventhub/Azure.Messaging.EventHubs/TROUBLESHOOTING.md)):
tune `RetryOptions` instead of looping around `SendAsync`. `Reason`, `IsTransient`, and the hub name
travel on the inner exception for the boundary's single log entry, so the catch adds what the
exception lacks (the batch size) and never logs or returns normally.
