# Azure Event Hubs: TypeScript SDK

Companion to `../SKILL.md`. Concepts, tables, and rules live in the skill body; this file holds the TypeScript code.

## Installation

```bash
npm install @azure/event-hubs @azure/identity @azure/eventhubs-checkpointstore-blob @azure/storage-blob
```

## Authentication

```typescript
import { EventHubProducerClient } from "@azure/event-hubs";
import { DefaultAzureCredential } from "@azure/identity";

const producer = new EventHubProducerClient(namespace, eventHubName, new DefaultAzureCredential());
```

## Producer: Batch Send

```typescript
let batch = await producer.createBatch();
for (const item of items) {
    if (!batch.tryAdd({ body: item })) {
        await producer.sendBatch(batch);
        batch = await producer.createBatch();
        if (!batch.tryAdd({ body: item })) {
            throw new Error("Event exceeds the maximum batch size");
        }
    }
}
await producer.sendBatch(batch);
await producer.close();
```

## Consumer: Production with Checkpointing

`EventHubConsumerClient` + `BlobCheckpointStore`:
```typescript
import { EventHubConsumerClient, type ReceivedEventData } from "@azure/event-hubs";
import { BlobCheckpointStore } from "@azure/eventhubs-checkpointstore-blob";
import { ContainerClient } from "@azure/storage-blob";

const checkpointStore = new BlobCheckpointStore(
    new ContainerClient(`https://${storageAccount}.blob.core.windows.net/${container}`, credential));

const consumer = new EventHubConsumerClient("$Default", ns, hub, credential, checkpointStore);

const stop = new AbortController();

const subscription = consumer.subscribe({
    processEvents: async (events, context) => {
        let handled: ReceivedEventData | undefined;
        for (const event of events) {
            if (stop.signal.aborted) break;
            try {
                await handleEvent(event, stop.signal);
            } catch (err) {
                if (stop.signal.aborted) {
                    if (err instanceof Error && err.name === "AbortError") break;
                    throw err;
                }
                const position = `Partition: [${context.partitionId}], SequenceNumber: [${event.sequenceNumber}]`;
                let parked = false;
                let parkError: unknown;
                try {
                    parked = await deadLetterStore.tryPark(event);
                } catch (thrown) {
                    parkError = thrown;
                }
                if (!parked) {
                    console.error(`Parking failed, stopping. ${position}`, { error: err, parkError });
                    stop.abort();
                    break;
                }
                console.error(`Parked event. ${position}`, err);
            }
            handled = event;
        }
        if (handled) await context.updateCheckpoint(handled);
    },
    processError: async (err, context) => console.error(`Error on partition [${context.partitionId}]`, err),
});

await new Promise<void>((resolve) => stop.signal.addEventListener("abort", () => resolve(), { once: true }));
await subscription.close();
await consumer.close();
```

An error that escapes `processEvents` goes to `processError`; a plain `Error` stops the partition
and resumes it from the last checkpoint, and one marked `retryable` keeps the pump reading, so the
next batch's checkpoint would move past the failed one. So the handler catches per event, and a park
that throws counts as a failed park, logged once with both errors on the `Parking failed` line.
Before `stop` is aborted, the only error that leaves the handler is a failed `updateCheckpoint`,
and every event before it was handled or parked; after the abort, each later batch breaks before
its first event. An event whose handler stopped on the aborted signal (an `AbortError`) ends the
batch without being checkpointed or reaching `processError`; the events before it are
checkpointed. Any other error the handler throws after the abort leaves the event unchecked too,
and reaches `processError`. `console` has no level above `error`, so the `Parking failed` prefix
is the string an alert matches: keep it fixed, or log through a structured logger that carries it
as a field. The host's own shutdown calls `stop.abort()` too; `close()` also releases the
partitions.
