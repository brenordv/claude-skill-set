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
        batch.tryAdd(event);
    }
}
if (batch.getCount() > 0) producer.send(batch);
```

## Consumer: Production with Checkpointing

`EventProcessorClient`:
```java
BlobContainerAsyncClient blobClient = new BlobContainerClientBuilder()
    .connectionString(storageConnStr).containerName("checkpoints").buildAsyncClient();

EventProcessorClient processor = new EventProcessorClientBuilder()
    .connectionString(ehConnStr, eventHubName)
    .consumerGroup("$Default")
    .checkpointStore(new BlobCheckpointStore(blobClient))
    .processEvent(ctx -> {
        System.out.println(ctx.getEventData().getBodyAsString());
        ctx.updateCheckpoint();
    })
    .processError(ctx -> System.err.println("Error: " + ctx.getThrowable().getMessage()))
    .buildEventProcessorClient();

processor.start();
// ... on shutdown:
processor.stop();
```

## Error Handling

```java
.processError(ctx -> {
    Throwable err = ctx.getThrowable();
    if (err instanceof AmqpException && ((AmqpException) err).isTransient()) {
        // SDK retries automatically
    } else {
        log.error("Non-transient error on partition {}: {}",
            ctx.getPartitionContext().getPartitionId(), err);
    }
})
```
