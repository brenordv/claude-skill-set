# Azure Event Hubs: Java SDK

Companion to `../SKILL.md`. Concepts, tables, and rules live in the skill body; this file holds the Java code.

## Installation

```xml
<dependency>
    <groupId>com.azure</groupId>
    <artifactId>azure-messaging-eventhubs</artifactId>
    <version>5.19.0</version>
</dependency>
<dependency>
    <groupId>com.azure</groupId>
    <artifactId>azure-messaging-eventhubs-checkpointstore-blob</artifactId>
    <version>1.20.0</version>
</dependency>
```

## Authentication

```java
EventHubProducerClient producer = new EventHubClientBuilder()
    .fullyQualifiedNamespace("<namespace>.servicebus.windows.net")
    .eventHubName("<event-hub-name>")
    .credential(new DefaultAzureCredentialBuilder().build())
    .buildProducerClient();
```

## Producer: Batch Send

```java
EventDataBatch batch = producer.createBatch();
for (String payload : payloads) {
    EventData event = new EventData(payload);
    if (!batch.tryAdd(event)) {
        producer.send(batch);
        batch = producer.createBatch();
        if (!batch.tryAdd(event)) {
            throw new IllegalArgumentException("Event exceeds the maximum batch size");
        }
    }
}
if (batch.getCount() > 0) producer.send(batch);
```

## Consumer: Production with Checkpointing

`EventProcessorClient`:
```java
// In the enclosing class:
private static final Marker PARK_FAILED = MarkerFactory.getMarker("PARK_FAILED");
```

```java
TokenCredential credential = new DefaultAzureCredentialBuilder().build();
BlobContainerAsyncClient blobClient = new BlobContainerClientBuilder()
    .endpoint("https://<account>.blob.core.windows.net")
    .containerName("checkpoints")
    .credential(credential)
    .buildAsyncClient();
CountDownLatch stopRequested = new CountDownLatch(1);

EventProcessorClient processor = new EventProcessorClientBuilder()
    .credential("<namespace>.servicebus.windows.net", eventHubName, credential)
    .consumerGroup("$Default")
    .checkpointStore(new BlobCheckpointStore(blobClient))
    .processEvent(ctx -> {
        if (stopRequested.getCount() == 0) {
            return;
        }

        EventData event = ctx.getEventData();
        String partitionId = ctx.getPartitionContext().getPartitionId();
        try {
            handleEvent(event);
        } catch (RuntimeException ex) {
            boolean parked;
            try {
                parked = deadLetterStore.tryPark(event);
            } catch (RuntimeException parkEx) {
                ex.addSuppressed(parkEx);
                parked = false;
            }
            if (!parked) {
                log.error(PARK_FAILED, "Parking failed, stopping. Partition: [{}], SequenceNumber: [{}]",
                    partitionId, event.getSequenceNumber(), ex);
                stopRequested.countDown();
                return;
            }

            log.error("Parked event. Partition: [{}], SequenceNumber: [{}]",
                partitionId, event.getSequenceNumber(), ex);
        }

        ctx.updateCheckpoint();
    })
    .processError(ctx -> {
        Throwable err = ctx.getThrowable();
        String partitionId = ctx.getPartitionContext().getPartitionId();
        if (err instanceof AmqpException && ((AmqpException) err).isTransient()) {
            log.warn("Transient error on partition {}; the SDK retries automatically", partitionId, err);
        } else {
            log.error("Non-transient error on partition {}", partitionId, err);
        }
    })
    .buildEventProcessorClient();

processor.start();
try {
    stopRequested.await();
} finally {
    processor.stop();
}
```

An exception thrown from `processEvent` never reaches `processError`; the SDK closes the partition
and it idles until ownership expires, then replays from the last checkpoint, so the callback catches
its own failure. SLF4J has no level above `ERROR`, so the park failure carries the `PARK_FAILED`
marker, which the logging backend can route to an alert; the parked line carries none. A park that
throws counts as a failed park: its exception rides on the handler's as suppressed, and the callback
logs with `PARK_FAILED` and stops.

The host thread calls `stop()` (it blocks up to 10 seconds), and the host's own shutdown counts down
the same latch; the callback never calls `stop()`. The enclosing method declares
`throws InterruptedException` for `await()`. `processError` sees only errors the processor recovers
from or reports itself: a transient one is a warning, any other an error, since it can recur while
nothing is consumed.

## Error Handling

The `processError` handler, with transient errors at warning and the rest at error, is part of the
production consumer above.
