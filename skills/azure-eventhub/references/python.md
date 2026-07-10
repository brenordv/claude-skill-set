# Azure Event Hubs: Python SDK

Companion to `../SKILL.md`. Concepts, tables, and rules live in the skill body; this file holds the Python code.

## Installation

```bash
pip install azure-eventhub azure-identity azure-eventhub-checkpointstoreblob-aio
```

## Authentication

```python
from azure.identity import DefaultAzureCredential
from azure.eventhub import EventHubProducerClient

producer = EventHubProducerClient(
    fully_qualified_namespace="<namespace>.servicebus.windows.net",
    eventhub_name="my-eventhub",
    credential=DefaultAzureCredential()
)
```

## Producer: Batch Send

```python
with producer:
    batch = producer.create_batch()
    for msg in messages:
        try:
            batch.add(EventData(msg))
        except ValueError:
            producer.send_batch(batch)
            batch = producer.create_batch()
            batch.add(EventData(msg))
    producer.send_batch(batch)
```

## Consumer: Production with Checkpointing

`EventHubConsumerClient` + `BlobCheckpointStore`:
```python
from azure.eventhub import EventHubConsumerClient
from azure.eventhub.extensions.checkpointstoreblob import BlobCheckpointStore

checkpoint_store = BlobCheckpointStore(
    blob_account_url="https://<account>.blob.core.windows.net",
    container_name="checkpoints", credential=DefaultAzureCredential())

consumer = EventHubConsumerClient(
    fully_qualified_namespace=ns, eventhub_name=hub,
    consumer_group="$Default", credential=DefaultAzureCredential(),
    checkpoint_store=checkpoint_store)

def on_event(partition_context, event):
    print(f"Received: {event.body_as_str()}")
    partition_context.update_checkpoint(event)

with consumer:
    consumer.receive(on_event=on_event)
```
