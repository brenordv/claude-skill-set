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
const batch = await producer.createBatch();
for (const item of items) {
    if (!batch.tryAdd({ body: item })) {
        await producer.sendBatch(batch);
        batch = await producer.createBatch();
        batch.tryAdd({ body: item });
    }
}
await producer.sendBatch(batch);
await producer.close();
```

## Consumer: Production with Checkpointing

`EventHubConsumerClient` + `BlobCheckpointStore`:
```typescript
import { BlobCheckpointStore } from "@azure/eventhubs-checkpointstore-blob";
import { ContainerClient } from "@azure/storage-blob";

const checkpointStore = new BlobCheckpointStore(
    new ContainerClient(`https://${storageAccount}.blob.core.windows.net/${container}`, credential));

const consumer = new EventHubConsumerClient("$Default", ns, hub, credential, checkpointStore);

const subscription = consumer.subscribe({
    processEvents: async (events, context) => {
        for (const event of events) console.log(event.body);
        if (events.length > 0) await context.updateCheckpoint(events[events.length - 1]);
    },
    processError: async (err, context) => console.error(err.message),
});
```
